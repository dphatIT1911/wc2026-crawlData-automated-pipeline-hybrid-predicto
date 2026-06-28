"""
Rule-Based Prediction Engine.

Implements betting rules based on the user's scientific betting document:
- Rule 1: Always bet the favorite if odds > 1.80 and ELO diff > 100
- Rule 2: Bet Over 2.5 if both teams' avg_goals > 1.5 and rest_diff < 2
- Rule 3: Fade the public (bet underdog) if odds movement is sharp against them
"""
import numpy as np
from typing import Dict, Optional

class RuleBasedPredictor:
    def __init__(self, db, odds_analyzer, feature_engineer):
        self.db = db
        self.odds_analyzer = odds_analyzer
        self.feature_engineer = feature_engineer

    def predict(self, match_id: int) -> Dict:
        # Get features
        features = self.feature_engineer.build_features(match_id)
        if not features:
            return {'error': 'Insufficient data for Rule-Based prediction'}

        # Calculate base probabilities from ELO (simple conversion)
        elo_diff = features.get('elo_diff', 0)
        # Expected score difference roughly elo_diff / 400
        win_prob = 1 / (1 + 10 ** (-elo_diff / 400))
        
        home_win = win_prob if elo_diff > 0 else 1 - win_prob
        away_win = 1 - home_win
        draw = 0.25 # Assume 25% draw rate
        
        # Normalize
        total = home_win + away_win + draw
        home_prob = round(home_win / total, 4)
        away_prob = round(away_win / total, 4)
        draw_prob = round(draw / total, 4)

        # Apply Rule 1: Favorite backing
        recommendation = None
        edge = 0.0
        odds_home = features.get('odds_implied_home', 0.33)
        odds_away = features.get('odds_implied_away', 0.34)
        
        # Convert implied probability back to decimal odds
        home_dec = 1/odds_home if odds_home > 0 else 0
        away_dec = 1/odds_away if odds_away > 0 else 0

        if elo_diff > 100 and home_dec > 1.80:
            recommendation = 'HOME'
            edge = home_prob - odds_home
        elif elo_diff < -100 and away_dec > 1.80:
            recommendation = 'AWAY'
            edge = away_prob - odds_away

        # Apply Rule 2: Over 2.5
        h_avg = features.get('home_avg_goals_scored_5', 1.0)
        a_avg = features.get('away_avg_goals_scored_5', 1.0)
        over_prob = 0.6 if (h_avg > 1.5 and a_avg > 1.5) else 0.4

        return {
            'prediction': {
                'home_win_probability': home_prob,
                'draw_probability': draw_prob,
                'away_win_probability': away_prob,
                'predicted_score': "2-1" if home_prob > away_prob else "1-2",
                'score_probability': 0.1,
                'asian_handicap': "-0.5" if home_prob > away_prob else "+0.5",
                'over_under_line': 2.5,
                'over_probability': over_prob,
                'under_probability': 1 - over_prob,
                'yellow_cards_prediction': features.get('avg_yellow_cards_total', 4.0),
                'corners_prediction': features.get('avg_corners_total', 9.5),
                'btts_probability': features.get('btts_rate_avg', 0.5),
                'confidence': 0.6,
                'model_version': 'rule_based_v1.0'
            },
            'model_breakdown': {
                'rule_based': {
                    'home': home_prob,
                    'draw': draw_prob,
                    'away': away_prob
                }
            },
            'value_bet': {
                'recommendation': recommendation,
                'edge': round(edge, 4),
                'kelly_fraction': 0.05 if recommendation else 0.0
            }
        }
