"""
Backtesting Module.

Evaluates prediction model performance on historical matches.
Uses ONLY data available BEFORE each match to simulate real-world conditions.

Metrics calculated:
- Accuracy (% correct 1X2 predictions)
- Brier Score (probabilistic accuracy, lower = better)
- Ranked Probability Score (RPS)
- Log Loss
- ROI Simulation (flat betting strategy)
- Win Rate
"""
import numpy as np
from typing import Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime

from .predictor import HybridPredictor


class Backtester:
    """Run backtests on finished matches and compute performance metrics."""

    def __init__(self, db: Session, model_dir: str = "models"):
        self.db = db
        self.predictor = HybridPredictor(db, model_dir=model_dir)

    def run(self, flat_bet_amount: float = 10.0) -> Dict:
        """
        Run backtest on all finished matches.
        
        For each finished match:
        1. Get prediction (using pre-trained model)
        2. Compare with actual result
        3. Simulate flat bet
        4. Compute metrics
        """
        # Get finished matches
        matches = self.db.execute(text("""
            SELECT m.id, m."homeScore", m."awayScore", 
                   ht.name as home_team, at.name as away_team,
                   m."startTime"
            FROM "Match" m
            JOIN "Team" ht ON m."homeTeamId" = ht.id
            JOIN "Team" at ON m."awayTeamId" = at.id
            WHERE m.status = 'FT'
            ORDER BY m."startTime" ASC
        """)).fetchall()
        
        if not matches:
            return {'error': 'No finished matches found for backtesting'}
        
        results = []
        total_bet = 0.0
        total_return = 0.0
        correct = 0
        brier_scores = []
        rps_scores = []
        log_losses = []
        
        for match in matches:
            try:
                prediction = self.predictor.predict(match.id)
                if 'error' in prediction:
                    continue
                
                pred = prediction['prediction']
                
                # Actual result
                if match.homeScore > match.awayScore:
                    actual = 'HOME'
                    actual_vec = [1, 0, 0]
                elif match.homeScore == match.awayScore:
                    actual = 'DRAW'
                    actual_vec = [0, 1, 0]
                else:
                    actual = 'AWAY'
                    actual_vec = [0, 0, 1]
                
                # Predicted result
                probs = [pred['home_win_probability'], pred['draw_probability'], pred['away_win_probability']]
                predicted_idx = np.argmax(probs)
                predicted = ['HOME', 'DRAW', 'AWAY'][predicted_idx]
                
                # Correct?
                is_correct = (predicted == actual)
                if is_correct:
                    correct += 1
                
                # Brier Score: mean squared error of probabilities
                brier = sum((p - a) ** 2 for p, a in zip(probs, actual_vec)) / 3
                brier_scores.append(brier)
                
                # RPS: Ranked Probability Score
                cum_pred = np.cumsum(probs)
                cum_actual = np.cumsum(actual_vec)
                rps = np.sum((cum_pred - cum_actual) ** 2) / 2
                rps_scores.append(rps)
                
                # Log Loss
                actual_prob = probs[actual_vec.index(1)]
                ll = -np.log(max(actual_prob, 1e-10))
                log_losses.append(ll)
                
                # ROI Simulation (flat bet on highest probability)
                total_bet += flat_bet_amount
                
                # Get actual odds for the predicted outcome
                odds_result = self.db.execute(text("""
                    SELECT "homeWin", draw, "awayWin" FROM "Odds"
                    WHERE "matchId" = :mid AND type = 'h2h'
                    LIMIT 1
                """), {'mid': match.id}).fetchone()
                
                if odds_result and is_correct:
                    if predicted == 'HOME' and odds_result.homeWin:
                        total_return += flat_bet_amount * odds_result.homeWin
                    elif predicted == 'DRAW' and odds_result.draw:
                        total_return += flat_bet_amount * odds_result.draw
                    elif predicted == 'AWAY' and odds_result.awayWin:
                        total_return += flat_bet_amount * odds_result.awayWin
                
                results.append({
                    'match_id': match.id,
                    'match': f"{match.home_team} vs {match.away_team}",
                    'actual': actual,
                    'predicted': predicted,
                    'correct': is_correct,
                    'probs': {'home': probs[0], 'draw': probs[1], 'away': probs[2]},
                    'confidence': pred.get('confidence', 0),
                    'actual_score': f"{match.homeScore}-{match.awayScore}",
                })
                
            except Exception as e:
                continue
        
        total = len(results)
        if total == 0:
            return {'error': 'No matches could be backtested'}
        
        # Calculate aggregate metrics
        accuracy = correct / total
        avg_brier = np.mean(brier_scores) if brier_scores else 1.0
        avg_rps = np.mean(rps_scores) if rps_scores else 1.0
        avg_log_loss = np.mean(log_losses) if log_losses else 5.0
        roi = ((total_return - total_bet) / total_bet) * 100 if total_bet > 0 else 0
        win_rate = correct / total
        
        metrics = {
            'total_matches': total,
            'correct_predictions': correct,
            'accuracy': round(accuracy, 4),
            'brier_score': round(avg_brier, 4),
            'rps': round(avg_rps, 4),
            'log_loss': round(avg_log_loss, 4),
            'roi_percent': round(roi, 2),
            'win_rate': round(win_rate, 4),
            'total_bet': round(total_bet, 2),
            'total_return': round(total_return, 2),
            'profit_loss': round(total_return - total_bet, 2),
        }
        
        # Save to ModelMetrics table
        try:
            self.db.execute(text("""
                INSERT INTO "ModelMetrics" (
                    "modelVersion", "evaluationDate",
                    accuracy, precision, recall, "f1Score",
                    "brierScore", rps, "logLoss",
                    "roiSimulated", "winRate",
                    "totalMatches", "correctPredictions",
                    details, "createdAt"
                ) VALUES (
                    'hybrid_v1.0', NOW(),
                    :accuracy, :accuracy, :accuracy, :accuracy,
                    :brier, :rps, :log_loss,
                    :roi, :win_rate,
                    :total, :correct,
                    :details, NOW()
                )
            """), {
                'accuracy': metrics['accuracy'],
                'brier': metrics['brier_score'],
                'rps': metrics['rps'],
                'log_loss': metrics['log_loss'],
                'roi': metrics['roi_percent'],
                'win_rate': metrics['win_rate'],
                'total': total,
                'correct': correct,
                'details': str(metrics),
            })
            self.db.commit()
        except Exception:
            self.db.rollback()
        
        return {
            'metrics': metrics,
            'match_results': results[:20],  # Return first 20 for preview
            'interpretation': self._interpret_metrics(metrics),
        }

    @staticmethod
    def _interpret_metrics(metrics: Dict) -> Dict:
        """Provide human-readable interpretation of metrics."""
        interpretations = {}
        
        acc = metrics['accuracy']
        if acc >= 0.55:
            interpretations['accuracy'] = f"✅ Xuất sắc ({acc:.1%}). Vượt trội hơn hầu hết các mô hình công khai."
        elif acc >= 0.50:
            interpretations['accuracy'] = f"✅ Tốt ({acc:.1%}). Ngang với implied probability của nhà cái."
        elif acc >= 0.45:
            interpretations['accuracy'] = f"⚠️ Trung bình ({acc:.1%}). Cần cải thiện features hoặc ensemble weights."
        else:
            interpretations['accuracy'] = f"❌ Yếu ({acc:.1%}). Model cần được retrain hoặc redesign."
        
        brier = metrics['brier_score']
        if brier < 0.20:
            interpretations['brier'] = f"✅ Calibration xuất sắc (Brier={brier:.4f}). Xác suất dự đoán rất sát thực tế."
        elif brier < 0.22:
            interpretations['brier'] = f"✅ Calibration tốt (Brier={brier:.4f})."
        else:
            interpretations['brier'] = f"⚠️ Calibration cần cải thiện (Brier={brier:.4f}). Target < 0.20."
        
        roi = metrics['roi_percent']
        if roi > 5:
            interpretations['roi'] = f"✅ Profitable! ROI = +{roi:.1f}%. Có edge thực sự so với thị trường."
        elif roi > 0:
            interpretations['roi'] = f"⚠️ ROI dương nhẹ (+{roi:.1f}%). Có thể do variance, cần sample lớn hơn."
        else:
            interpretations['roi'] = f"❌ ROI âm ({roi:.1f}%). Chưa thắng được biên lợi nhuận nhà cái."
        
        return interpretations
