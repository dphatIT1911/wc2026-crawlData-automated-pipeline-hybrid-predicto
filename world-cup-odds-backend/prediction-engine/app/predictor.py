"""
Hybrid Prediction Engine.

Combines three prediction sources:
1. Dixon-Coles Statistical Model (weight: 0.30)
2. Odds Market Intelligence (weight: 0.40) 
3. CatBoost ML Model (weight: 0.30)

The weights reflect the empirical finding that odds market is the single
best predictor, but can be improved by combining with statistical and ML models.
"""
import numpy as np
import pandas as pd
import pickle
import os
import json
from typing import Dict, Optional, List, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

from .dixon_coles import DixonColesModel
from .odds_analyzer import OddsAnalyzer
from .features import FeatureEngineer

# Try to import CatBoost (optional - degrades gracefully)
try:
    from catboost import CatBoostClassifier
    HAS_CATBOOST = True
except ImportError:
    HAS_CATBOOST = False


class HybridPredictor:
    """
    Hybrid football prediction engine combining statistical, market, and ML models.
    """

    def __init__(self, db: Session, model_dir: str = "models"):
        self.db = db
        self.model_dir = model_dir
        self.feature_engineer = FeatureEngineer(db)
        self.odds_analyzer = OddsAnalyzer()
        
        # Model instances
        self.dixon_coles: Optional[DixonColesModel] = None
        self.catboost_model = None
        
        # Ensemble weights (calibrated via backtest)
        self.weights = {
            'dixon_coles': 0.30,
            'odds_market': 0.40,
            'catboost': 0.30,
        }
        
        # Load models if available
        self._load_models()

    def _load_models(self):
        """Load pre-trained models from disk."""
        dc_path = os.path.join(self.model_dir, "dixon_coles.pkl")
        cb_path = os.path.join(self.model_dir, "catboost_model.cbm")
        weights_path = os.path.join(self.model_dir, "ensemble_weights.json")
        
        if os.path.exists(dc_path):
            with open(dc_path, 'rb') as f:
                self.dixon_coles = pickle.load(f)
        
        if HAS_CATBOOST and os.path.exists(cb_path):
            self.catboost_model = CatBoostClassifier()
            self.catboost_model.load_model(cb_path)
        
        if os.path.exists(weights_path):
            with open(weights_path, 'r') as f:
                self.weights = json.load(f)

    def train_dixon_coles(self, xi: float = 0.005):
        """Train Dixon-Coles model on all finished matches in database."""
        results = self.db.execute(text("""
            SELECT m.id, ht.name as home_team, at.name as away_team,
                   m."homeScore" as home_goals, m."awayScore" as away_goals,
                   m."startTime" as start_time
            FROM "Match" m
            JOIN "Team" ht ON m."homeTeamId" = ht.id
            JOIN "Team" at ON m."awayTeamId" = at.id
            WHERE m.status = 'FT'
            ORDER BY m."startTime" ASC
        """)).fetchall()
        
        if len(results) < 5:
            raise ValueError(f"Need at least 5 finished matches, got {len(results)}")
        
        home_teams = [r.home_team for r in results]
        away_teams = [r.away_team for r in results]
        home_goals = [r.home_goals for r in results]
        away_goals = [r.away_goals for r in results]
        
        # Calculate days ago for time-decay
        from datetime import datetime
        now = datetime.utcnow()
        days_ago = [(now - r.start_time).days for r in results]
        
        self.dixon_coles = DixonColesModel(xi=xi)
        self.dixon_coles.fit(home_teams, away_teams, home_goals, away_goals, days_ago)
        
        # Save model
        os.makedirs(self.model_dir, exist_ok=True)
        with open(os.path.join(self.model_dir, "dixon_coles.pkl"), 'wb') as f:
            pickle.dump(self.dixon_coles, f)
        
        return self.dixon_coles.get_team_strengths()

    def train_catboost(self):
        """Train CatBoost model on finished matches with features."""
        if not HAS_CATBOOST:
            raise ImportError("CatBoost is not installed. Run: pip install catboost")
        
        # Get all finished matches
        results = self.db.execute(text("""
            SELECT id, "homeScore", "awayScore" FROM "Match" WHERE status = 'FT' ORDER BY "startTime" ASC
        """)).fetchall()
        
        match_ids = [r.id for r in results]
        labels = []
        for r in results:
            if r.homeScore > r.awayScore:
                labels.append(0)  # Home win
            elif r.homeScore == r.awayScore:
                labels.append(1)  # Draw
            else:
                labels.append(2)  # Away win
        
        # Build features
        df = self.feature_engineer.build_features_batch(match_ids)
        if df.empty or len(df) < 10:
            raise ValueError(f"Not enough feature data. Got {len(df)} rows.")
        
        feature_names = FeatureEngineer.get_feature_names()
        
        # Align labels with features (some matches might not have features)
        valid_ids = set(df['match_id'].values)
        valid_labels = [labels[i] for i, mid in enumerate(match_ids) if mid in valid_ids]
        
        X = df[feature_names].fillna(0).values
        y = np.array(valid_labels)
        
        # Time-based split: last 20% for validation
        split = int(len(X) * 0.8)
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]
        
        model = CatBoostClassifier(
            iterations=500,
            learning_rate=0.05,
            depth=6,
            loss_function='MultiClass',
            eval_metric='MultiClass',
            random_seed=42,
            verbose=50,
        )
        
        model.fit(X_train, y_train, eval_set=(X_val, y_val), early_stopping_rounds=50)
        
        self.catboost_model = model
        os.makedirs(self.model_dir, exist_ok=True)
        model.save_model(os.path.join(self.model_dir, "catboost_model.cbm"))
        
        # Feature importance
        importance = dict(zip(feature_names, model.feature_importances_))
        sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'train_size': len(X_train),
            'val_size': len(X_val),
            'feature_importance': sorted_imp[:15],
        }

    def predict(self, match_id: int) -> Dict:
        """
        Generate hybrid prediction for a match.
        
        Returns comprehensive prediction including:
        - 1X2 probabilities (ensemble)
        - Predicted score
        - Asian Handicap
        - Over/Under
        - Yellow cards & corners predictions
        - BTTS
        - Value bet recommendation
        - Model breakdown
        """
        # Get match info
        match = self.db.execute(text("""
            SELECT m.*, ht.name as home_team_name, at.name as away_team_name
            FROM "Match" m
            JOIN "Team" ht ON m."homeTeamId" = ht.id
            JOIN "Team" at ON m."awayTeamId" = at.id
            WHERE m.id = :match_id
        """), {'match_id': match_id}).fetchone()
        
        if not match:
            return {'error': f'Match {match_id} not found'}
        
        match_data = dict(match._mapping)
        
        # === Tầng 1: Dixon-Coles ===
        dc_pred = self._predict_dixon_coles(match_data)
        
        # === Tầng 2: Odds Market ===
        odds_pred = self._predict_odds_market(match_id)
        
        # === Tầng 3: CatBoost ML ===
        ml_pred = self._predict_catboost(match_id)
        
        # === Ensemble ===
        ensemble = self._ensemble(dc_pred, odds_pred, ml_pred)
        
        # === Derive additional markets ===
        predicted_score = self._derive_predicted_score(dc_pred, ensemble)
        ou_pred = self._derive_over_under(dc_pred)
        btts = dc_pred.get('btts_prob', 0.5) if dc_pred else 0.5
        cards_corners = self._predict_cards_corners(match_data)
        value_bet = self._find_value_bet(ensemble, odds_pred)
        
        # === Build response ===
        result = {
            'matchId': match_id,
            'homeTeam': match_data.get('home_team_name', ''),
            'awayTeam': match_data.get('away_team_name', ''),
            'startTime': str(match_data.get('startTime', '')),
            
            'prediction': {
                'home_win_probability': ensemble['home'],
                'draw_probability': ensemble['draw'],
                'away_win_probability': ensemble['away'],
                
                'predicted_score': f"{predicted_score[0]}-{predicted_score[1]}",
                'score_probability': predicted_score[2],
                
                'asian_handicap': self._derive_asian_handicap(ensemble),
                'over_under_line': 2.5,
                'over_probability': ou_pred.get('over_2.5', 0.5),
                'under_probability': ou_pred.get('under_2.5', 0.5),
                
                'yellow_cards_prediction': cards_corners['yellow_cards'],
                'corners_prediction': cards_corners['corners'],
                
                'btts_probability': round(btts, 4),
                
                'confidence': self._calculate_confidence(ensemble, dc_pred, odds_pred, ml_pred),
                'model_version': 'hybrid_v1.0',
            },
            
            'model_breakdown': {
                'dixon_coles': dc_pred if dc_pred else {'home': 0.33, 'draw': 0.33, 'away': 0.34},
                'odds_market': odds_pred if odds_pred else {'home': 0.33, 'draw': 0.33, 'away': 0.34},
                'catboost': ml_pred if ml_pred else {'home': 0.33, 'draw': 0.33, 'away': 0.34},
            },
            
            'value_bet': value_bet,
        }
        
        # Save prediction to database
        self._save_prediction(match_id, result)
        
        return result

    def _predict_dixon_coles(self, match_data: Dict) -> Optional[Dict]:
        """Get prediction from Dixon-Coles model."""
        if self.dixon_coles is None or not self.dixon_coles._fitted:
            return None
        
        try:
            pred = self.dixon_coles.predict(
                match_data.get('home_team_name', ''),
                match_data.get('away_team_name', '')
            )
            return {
                'home': pred['home_win_prob'],
                'draw': pred['draw_prob'],
                'away': pred['away_win_prob'],
                'btts_prob': pred.get('btts_prob', 0.5),
                'expected_home_goals': pred.get('expected_home_goals', 1.2),
                'expected_away_goals': pred.get('expected_away_goals', 1.0),
                'over_2.5': pred.get('over_2.5', 0.5),
                'under_2.5': pred.get('under_2.5', 0.5),
                'over_1.5': pred.get('over_1.5', 0.7),
                'under_1.5': pred.get('under_1.5', 0.3),
                'over_3.5': pred.get('over_3.5', 0.3),
                'under_3.5': pred.get('under_3.5', 0.7),
                'predicted_home_score': pred.get('predicted_home_score', 1),
                'predicted_away_score': pred.get('predicted_away_score', 0),
                'score_probability': pred.get('score_probability', 0.1),
            }
        except Exception:
            return None

    def _predict_odds_market(self, match_id: int) -> Optional[Dict]:
        """Get implied probabilities from odds market."""
        odds = self.db.execute(text("""
            SELECT * FROM "Odds" WHERE "matchId" = :mid
        """), {'mid': match_id}).fetchall()
        
        odds_list = [dict(r._mapping) for r in odds]
        analysis = self.odds_analyzer.analyze_match_odds(odds_list)
        
        probs = analysis.get('implied_probs', {})
        if probs.get('home', 0) > 0:
            return {
                'home': probs['home'],
                'draw': probs['draw'],
                'away': probs['away'],
            }
        return None

    def _predict_catboost(self, match_id: int) -> Optional[Dict]:
        """Get prediction from CatBoost model."""
        if self.catboost_model is None:
            return None
        
        try:
            features = self.feature_engineer.build_features(match_id)
            if features is None:
                return None
            
            feature_names = FeatureEngineer.get_feature_names()
            X = np.array([[features.get(f, 0.0) for f in feature_names]])
            
            probs = self.catboost_model.predict_proba(X)[0]
            return {
                'home': round(float(probs[0]), 4),
                'draw': round(float(probs[1]), 4),
                'away': round(float(probs[2]), 4),
            }
        except Exception:
            return None

    def _ensemble(self, dc: Optional[Dict], odds: Optional[Dict], ml: Optional[Dict]) -> Dict:
        """Weighted ensemble of available models."""
        sources = []
        weights = []
        
        if dc:
            sources.append(dc)
            weights.append(self.weights['dixon_coles'])
        if odds:
            sources.append(odds)
            weights.append(self.weights['odds_market'])
        if ml:
            sources.append(ml)
            weights.append(self.weights['catboost'])
        
        if not sources:
            return {'home': 0.33, 'draw': 0.33, 'away': 0.34}
        
        # Normalize weights
        total_w = sum(weights)
        weights = [w / total_w for w in weights]
        
        home = sum(s['home'] * w for s, w in zip(sources, weights))
        draw = sum(s['draw'] * w for s, w in zip(sources, weights))
        away = sum(s['away'] * w for s, w in zip(sources, weights))
        
        # Normalize probabilities
        total = home + draw + away
        return {
            'home': round(home / total, 4),
            'draw': round(draw / total, 4),
            'away': round(away / total, 4),
        }

    def _derive_predicted_score(self, dc: Optional[Dict], ensemble: Dict) -> Tuple[int, int, float]:
        """Derive most likely score from Dixon-Coles matrix or ensemble."""
        if dc and 'predicted_home_score' in dc:
            return (dc['predicted_home_score'], dc['predicted_away_score'], dc.get('score_probability', 0.1))
        
        # Fallback: use simple heuristic from ensemble
        if ensemble['home'] > ensemble['away']:
            return (1, 0, round(ensemble['home'] * 0.25, 4))
        elif ensemble['away'] > ensemble['home']:
            return (0, 1, round(ensemble['away'] * 0.25, 4))
        else:
            return (1, 1, round(ensemble['draw'] * 0.35, 4))

    def _derive_over_under(self, dc: Optional[Dict]) -> Dict:
        """Derive Over/Under probabilities."""
        if dc and 'over_2.5' in dc:
            return {
                'over_1.5': dc.get('over_1.5', 0.7),
                'under_1.5': dc.get('under_1.5', 0.3),
                'over_2.5': dc.get('over_2.5', 0.5),
                'under_2.5': dc.get('under_2.5', 0.5),
                'over_3.5': dc.get('over_3.5', 0.3),
                'under_3.5': dc.get('under_3.5', 0.7),
            }
        return {'over_2.5': 0.5, 'under_2.5': 0.5}

    def _derive_asian_handicap(self, ensemble: Dict) -> str:
        """Derive recommended Asian Handicap line from probabilities."""
        diff = ensemble['home'] - ensemble['away']
        if diff > 0.25:
            return "-1.0"
        elif diff > 0.15:
            return "-0.75"
        elif diff > 0.08:
            return "-0.5"
        elif diff > 0.02:
            return "-0.25"
        elif diff > -0.02:
            return "0"
        elif diff > -0.08:
            return "+0.25"
        elif diff > -0.15:
            return "+0.5"
        elif diff > -0.25:
            return "+0.75"
        else:
            return "+1.0"

    def _predict_cards_corners(self, match_data: Dict) -> Dict:
        """Predict yellow cards and corners from team stats."""
        home_id = match_data.get('homeTeamId')
        away_id = match_data.get('awayTeamId')
        
        # Get team stats
        def get_stat(team_id, field, default):
            r = self.db.execute(text(f"""
                SELECT "{field}" FROM "TeamStats" 
                WHERE "teamId" = :tid
                ORDER BY "snapshotDate" DESC LIMIT 1
            """), {'tid': team_id}).fetchone()
            return float(r[0]) if r and r[0] is not None else default
        
        yc_home = get_stat(home_id, 'avgYellowCards', 2.0)
        yc_away = get_stat(away_id, 'avgYellowCards', 2.0)
        corners_home = get_stat(home_id, 'avgCorners', 5.0)
        corners_away = get_stat(away_id, 'avgCorners', 5.0)
        
        return {
            'yellow_cards': round(yc_home + yc_away, 1),
            'corners': round(corners_home + corners_away, 1),
        }

    def _calculate_confidence(self, ensemble: Dict, dc: Optional[Dict], 
                               odds: Optional[Dict], ml: Optional[Dict]) -> float:
        """
        Calculate prediction confidence based on:
        1. Agreement between models
        2. Strength of the prediction (how far from 33/33/33)
        3. Number of available models
        """
        sources = [s for s in [dc, odds, ml] if s is not None]
        n_models = len(sources)
        
        if n_models == 0:
            return 0.0
        
        # Agreement: low variance between models = high confidence
        if n_models >= 2:
            homes = [s['home'] for s in sources]
            agreement = 1.0 - np.std(homes) * 3  # Penalize disagreement
            agreement = max(0.0, min(1.0, agreement))
        else:
            agreement = 0.5
        
        # Strength: how decisive is the prediction
        max_prob = max(ensemble['home'], ensemble['draw'], ensemble['away'])
        strength = (max_prob - 0.33) / 0.67  # 0 if uniform, 1 if certain
        strength = max(0.0, min(1.0, strength))
        
        # Model coverage bonus
        coverage = n_models / 3.0
        
        confidence = 0.4 * agreement + 0.35 * strength + 0.25 * coverage
        return round(max(0.1, min(0.99, confidence)), 2)

    def _find_value_bet(self, ensemble: Dict, odds_pred: Optional[Dict]) -> Dict:
        """Find value bets where our model differs from market."""
        if not odds_pred:
            return {'recommendation': None, 'edge': 0.0}
        
        edges = {
            'HOME': ensemble['home'] - odds_pred['home'],
            'DRAW': ensemble['draw'] - odds_pred['draw'],
            'AWAY': ensemble['away'] - odds_pred['away'],
        }
        
        best_type = max(edges, key=edges.get)
        best_edge = edges[best_type]
        
        if best_edge < 0.03:  # Need at least 3% edge
            return {'recommendation': None, 'edge': 0.0}
        
        # Kelly fraction: f = (bp - q) / b where b = odds-1, p = our prob, q = 1-p
        our_prob = ensemble[best_type.lower()]
        market_odds = 1.0 / odds_pred[best_type.lower()]  # Convert prob to decimal odds
        b = market_odds - 1
        kelly = (b * our_prob - (1 - our_prob)) / b if b > 0 else 0
        kelly = max(0, min(kelly, 0.1))  # Cap at 10% of bankroll
        
        return {
            'recommendation': best_type,
            'edge': round(best_edge, 4),
            'kelly_fraction': round(kelly, 4),
        }

    def _save_prediction(self, match_id: int, result: Dict):
        """Save prediction to database."""
        try:
            pred = result['prediction']
            breakdown = result['model_breakdown']
            vb = result.get('value_bet', {})
            
            self.db.execute(text("""
                INSERT INTO "Prediction" (
                    "matchId", "modelVersion",
                    "homeWinProb", "drawProb", "awayWinProb",
                    "predictedHomeScore", "predictedAwayScore", "scoreProbability",
                    "asianHandicap", "overUnderLine", "overProb", "underProb",
                    "predictedYellowCards", "predictedCorners",
                    "bttsProb", "confidence",
                    "dcHomeProb", "dcDrawProb", "dcAwayProb",
                    "omHomeProb", "omDrawProb", "omAwayProb",
                    "mlHomeProb", "mlDrawProb", "mlAwayProb",
                    "valueBetType", "valueBetEdge", "kellyFraction",
                    "createdAt"
                ) VALUES (
                    :matchId, :modelVersion,
                    :homeWinProb, :drawProb, :awayWinProb,
                    :predictedHomeScore, :predictedAwayScore, :scoreProbability,
                    :asianHandicap, :overUnderLine, :overProb, :underProb,
                    :predictedYellowCards, :predictedCorners,
                    :bttsProb, :confidence,
                    :dcHome, :dcDraw, :dcAway,
                    :omHome, :omDraw, :omAway,
                    :mlHome, :mlDraw, :mlAway,
                    :vbType, :vbEdge, :vbKelly,
                    NOW()
                )
                ON CONFLICT ("matchId", "modelVersion") 
                DO UPDATE SET
                    "homeWinProb" = EXCLUDED."homeWinProb",
                    "drawProb" = EXCLUDED."drawProb",
                    "awayWinProb" = EXCLUDED."awayWinProb",
                    "predictedHomeScore" = EXCLUDED."predictedHomeScore",
                    "predictedAwayScore" = EXCLUDED."predictedAwayScore",
                    "confidence" = EXCLUDED."confidence",
                    "createdAt" = NOW()
            """), {
                'matchId': match_id,
                'modelVersion': 'hybrid_v1.0',
                'homeWinProb': pred['home_win_probability'],
                'drawProb': pred['draw_probability'],
                'awayWinProb': pred['away_win_probability'],
                'predictedHomeScore': int(pred['predicted_score'].split('-')[0]),
                'predictedAwayScore': int(pred['predicted_score'].split('-')[1]),
                'scoreProbability': pred.get('score_probability'),
                'asianHandicap': pred.get('asian_handicap'),
                'overUnderLine': 2.5,
                'overProb': pred.get('over_probability'),
                'underProb': pred.get('under_probability'),
                'predictedYellowCards': pred.get('yellow_cards_prediction'),
                'predictedCorners': pred.get('corners_prediction'),
                'bttsProb': pred.get('btts_probability'),
                'confidence': pred.get('confidence', 0.5),
                'dcHome': breakdown['dixon_coles']['home'],
                'dcDraw': breakdown['dixon_coles']['draw'],
                'dcAway': breakdown['dixon_coles']['away'],
                'omHome': breakdown['odds_market']['home'],
                'omDraw': breakdown['odds_market']['draw'],
                'omAway': breakdown['odds_market']['away'],
                'mlHome': breakdown['catboost']['home'],
                'mlDraw': breakdown['catboost']['draw'],
                'mlAway': breakdown['catboost']['away'],
                'vbType': vb.get('recommendation'),
                'vbEdge': vb.get('edge', 0),
                'vbKelly': vb.get('kelly_fraction', 0),
            })
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            # Non-critical: prediction still returned even if save fails
            pass
