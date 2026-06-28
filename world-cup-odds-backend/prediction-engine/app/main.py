"""
Prediction Engine - FastAPI Application.

Provides REST API endpoints for the NestJS backend to call.
"""
import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

from .database import get_db, engine
from .predictor import HybridPredictor

app = FastAPI(
    title="Football Prediction Engine",
    description="Hybrid Dixon-Coles + Odds Market + CatBoost prediction engine for World Cup 2026",
    version="1.0.0",
)


from .rule_based import RuleBasedPredictor

@app.get("/")
def root():
    return {"status": "ok", "service": "prediction-engine", "version": "1.0.0"}


@app.get("/ping")
def ping():
    return "OK"


@app.get("/prediction/match/{match_id}")
def predict_match(match_id: int, model_type: str = "hybrid", db: Session = Depends(get_db)):
    """
    Generate prediction for a specific match.
    model_type: 'hybrid' or 'rule_based'
    """
    if model_type == "rule_based":
        from .predictor import FeatureEngineer, OddsAnalyzer
        predictor = RuleBasedPredictor(db, OddsAnalyzer(), FeatureEngineer(db))
        result = predictor.predict(match_id)
    else:
        predictor = HybridPredictor(db, model_dir="models")
        result = predictor.predict(match_id)
    
    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])
    
    return result


@app.get("/prediction/upcoming")
def predict_upcoming(model_type: str = "hybrid", db: Session = Depends(get_db)):
    """Predict all upcoming (not started) matches."""
    matches = db.execute(text("""
        SELECT m.id, ht.name as home_team, at.name as away_team, m."startTime"
        FROM "Match" m
        JOIN "Team" ht ON m."homeTeamId" = ht.id
        JOIN "Team" at ON m."awayTeamId" = at.id
        WHERE m.status = 'NS'
        ORDER BY m."startTime" ASC
    """)).fetchall()
    
    if model_type == "rule_based":
        from .predictor import FeatureEngineer, OddsAnalyzer
        predictor = RuleBasedPredictor(db, OddsAnalyzer(), FeatureEngineer(db))
    else:
        predictor = HybridPredictor(db, model_dir="models")
        
    predictions = []
    
    for match in matches:
        try:
            pred = predictor.predict(match.id)
            predictions.append(pred)
        except Exception as e:
            predictions.append({
                'matchId': match.id,
                'error': str(e),
                'homeTeam': match.home_team,
                'awayTeam': match.away_team,
            })
    
    return {
        'total': len(predictions),
        'predictions': predictions,
    }


@app.post("/prediction/train")
def train_models(db: Session = Depends(get_db)):
    """Train/retrain all models."""
    predictor = HybridPredictor(db, model_dir="models")
    
    results = {}
    
    # Train Dixon-Coles
    try:
        dc_result = predictor.train_dixon_coles()
        results['dixon_coles'] = {
            'status': 'success',
            'teams': len(dc_result),
        }
    except Exception as e:
        results['dixon_coles'] = {'status': 'error', 'message': str(e)}
    
    # Train CatBoost
    try:
        cb_result = predictor.train_catboost()
        results['catboost'] = {
            'status': 'success',
            **cb_result,
        }
    except Exception as e:
        results['catboost'] = {'status': 'error', 'message': str(e)}
    
    return results


@app.get("/prediction/backtest")
def run_backtest(db: Session = Depends(get_db)):
    """Run backtest on all finished matches."""
    from .backtest import Backtester
    
    backtester = Backtester(db, model_dir="models")
    results = backtester.run()
    
    return results


@app.get("/prediction/model-metrics")
def get_model_metrics(db: Session = Depends(get_db)):
    """Get stored model performance metrics."""
    results = db.execute(text("""
        SELECT * FROM "ModelMetrics"
        ORDER BY "evaluationDate" DESC
        LIMIT 10
    """)).fetchall()
    
    return [dict(r._mapping) for r in results]


@app.get("/prediction/team-strengths")
def get_team_strengths(db: Session = Depends(get_db)):
    """Get Dixon-Coles team attack/defense ratings."""
    predictor = HybridPredictor(db, model_dir="models")
    
    if predictor.dixon_coles and predictor.dixon_coles._fitted:
        strengths = predictor.dixon_coles.get_team_strengths()
        # Sort by attack rating
        sorted_teams = sorted(strengths.items(), key=lambda x: x[1]['attack'], reverse=True)
        return {'teams': dict(sorted_teams)}
    
    return {'teams': {}, 'message': 'Dixon-Coles model not trained yet. Call POST /prediction/train first.'}
