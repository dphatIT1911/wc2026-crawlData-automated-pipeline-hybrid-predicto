"""
Feature Engineering Module.

Builds feature vectors for each match from database data.
Features are organized into 4 groups:
1. Team Strength (ELO, FIFA Ranking, Form)
2. Head-to-Head History
3. Odds Market Intelligence
4. Match Context
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.orm import Session


class FeatureEngineer:
    """Build feature vectors for match prediction."""

    def __init__(self, db: Session):
        self.db = db

    def build_features(self, match_id: int) -> Optional[Dict[str, float]]:
        """
        Build complete feature vector for a match.
        
        Returns None if insufficient data.
        """
        # Get match info
        match = self._get_match(match_id)
        if not match:
            return None
        
        features = {}
        
        # 1. Team Strength Features
        home_stats = self._get_team_stats(match['home_team_id'], match['start_time'])
        away_stats = self._get_team_stats(match['away_team_id'], match['start_time'])
        features.update(self._team_strength_features(home_stats, away_stats))
        
        # 2. H2H Features
        h2h = self._get_h2h(match['home_team_id'], match['away_team_id'])
        features.update(self._h2h_features(h2h, match['home_team_id']))
        
        # 3. Odds Features
        odds = self._get_odds(match_id)
        features.update(self._odds_features(odds))
        
        # 4. Match Context
        features.update(self._context_features(match))
        
        return features

    def build_features_batch(self, match_ids: List[int]) -> pd.DataFrame:
        """Build features for multiple matches, return as DataFrame."""
        rows = []
        for mid in match_ids:
            feats = self.build_features(mid)
            if feats:
                feats['match_id'] = mid
                rows.append(feats)
        return pd.DataFrame(rows)

    def _get_match(self, match_id: int) -> Optional[Dict]:
        result = self.db.execute(text("""
            SELECT m.id, m."homeTeamId" as home_team_id, m."awayTeamId" as away_team_id,
                   m."startTime" as start_time, m.status,
                   m."homeScore" as home_score, m."awayScore" as away_score,
                   ht.name as home_team_name, at.name as away_team_name
            FROM "Match" m
            JOIN "Team" ht ON m."homeTeamId" = ht.id
            JOIN "Team" at ON m."awayTeamId" = at.id
            WHERE m.id = :match_id
        """), {'match_id': match_id}).fetchone()
        
        if not result:
            return None
        return dict(result._mapping)

    def _get_team_stats(self, team_id: int, before_date) -> Optional[Dict]:
        """Get most recent team stats snapshot before match date."""
        result = self.db.execute(text("""
            SELECT * FROM "TeamStats"
            WHERE "teamId" = :team_id AND "snapshotDate" <= :before_date
            ORDER BY "snapshotDate" DESC
            LIMIT 1
        """), {'team_id': team_id, 'before_date': before_date}).fetchone()
        
        if result:
            return dict(result._mapping)
        
        # Fallback: get latest stats regardless of date
        result = self.db.execute(text("""
            SELECT * FROM "TeamStats"
            WHERE "teamId" = :team_id
            ORDER BY "snapshotDate" DESC
            LIMIT 1
        """), {'team_id': team_id}).fetchone()
        
        return dict(result._mapping) if result else None

    def _get_h2h(self, team1_id: int, team2_id: int) -> Optional[Dict]:
        t1, t2 = min(team1_id, team2_id), max(team1_id, team2_id)
        result = self.db.execute(text("""
            SELECT * FROM "H2HRecord"
            WHERE "team1Id" = :t1 AND "team2Id" = :t2
        """), {'t1': t1, 't2': t2}).fetchone()
        return dict(result._mapping) if result else None

    def _get_odds(self, match_id: int) -> List[Dict]:
        results = self.db.execute(text("""
            SELECT * FROM "Odds"
            WHERE "matchId" = :match_id
        """), {'match_id': match_id}).fetchall()
        return [dict(r._mapping) for r in results]

    # ---- Feature Builders ----

    def _team_strength_features(self, home: Optional[Dict], away: Optional[Dict]) -> Dict[str, float]:
        features = {}
        
        # Default values for missing stats
        def safe(stats, key, default=0.0):
            if stats is None:
                return default
            val = stats.get(key)
            return float(val) if val is not None else default
        
        # ELO & FIFA Ranking diff
        features['elo_diff'] = safe(home, 'eloRating', 1500) - safe(away, 'eloRating', 1500)
        features['fifa_rank_diff'] = safe(away, 'fifaRanking', 50) - safe(home, 'fifaRanking', 50)  # Lower rank = better
        
        # Form
        features['form_points_diff_5'] = safe(home, 'formPoints5', 1.5) - safe(away, 'formPoints5', 1.5)
        features['form_points_diff_10'] = safe(home, 'formPoints10', 1.5) - safe(away, 'formPoints10', 1.5)
        
        # Goal stats
        features['avg_goals_scored_diff'] = safe(home, 'avgGoalsScored5', 1.2) - safe(away, 'avgGoalsScored5', 1.2)
        features['avg_goals_conceded_diff'] = safe(home, 'avgGoalsConceded5', 1.0) - safe(away, 'avgGoalsConceded5', 1.0)
        features['home_avg_goals_scored_5'] = safe(home, 'avgGoalsScored5', 1.2)
        features['away_avg_goals_scored_5'] = safe(away, 'avgGoalsScored5', 1.2)
        features['home_avg_goals_conceded_5'] = safe(home, 'avgGoalsConceded5', 1.0)
        features['away_avg_goals_conceded_5'] = safe(away, 'avgGoalsConceded5', 1.0)
        
        # Home/Away rates
        features['home_win_rate'] = safe(home, 'homeWinRate', 0.45)
        features['away_win_rate'] = safe(away, 'awayWinRate', 0.30)
        
        # Discipline
        features['avg_yellow_cards_total'] = safe(home, 'avgYellowCards', 2.0) + safe(away, 'avgYellowCards', 2.0)
        features['avg_corners_diff'] = safe(home, 'avgCorners', 5.0) - safe(away, 'avgCorners', 5.0)
        features['avg_corners_total'] = safe(home, 'avgCorners', 5.0) + safe(away, 'avgCorners', 5.0)
        
        # Advanced
        features['clean_sheet_rate_diff'] = safe(home, 'cleanSheetRate', 0.3) - safe(away, 'cleanSheetRate', 0.3)
        features['btts_rate_avg'] = (safe(home, 'bttsRate', 0.5) + safe(away, 'bttsRate', 0.5)) / 2
        
        return features

    def _h2h_features(self, h2h: Optional[Dict], home_team_id: int) -> Dict[str, float]:
        features = {}
        
        if h2h is None or h2h.get('totalMatches', 0) == 0:
            features['h2h_home_win_rate'] = 0.33
            features['h2h_draw_rate'] = 0.33
            features['h2h_avg_total_goals'] = 2.5
            features['h2h_total_matches'] = 0
            return features
        
        total = h2h['totalMatches']
        
        # Determine which team is team1 vs team2
        t1 = min(home_team_id, h2h.get('team2Id', 0))
        is_home_team1 = (home_team_id == h2h.get('team1Id'))
        
        home_wins = h2h['team1Wins'] if is_home_team1 else h2h['team2Wins']
        away_wins = h2h['team2Wins'] if is_home_team1 else h2h['team1Wins']
        
        features['h2h_home_win_rate'] = home_wins / total
        features['h2h_draw_rate'] = h2h['draws'] / total
        features['h2h_avg_total_goals'] = (h2h['team1Goals'] + h2h['team2Goals']) / total
        features['h2h_total_matches'] = float(total)
        
        return features

    def _odds_features(self, odds: List[Dict]) -> Dict[str, float]:
        features = {}
        
        # Find best h2h odds (prefer Pinnacle)
        h2h = [o for o in odds if o.get('type') == 'h2h']
        pinnacle = next((o for o in h2h if 'Pinnacle' in str(o.get('bookmaker', ''))), None)
        best = pinnacle or (h2h[0] if h2h else None)
        
        if best and best.get('homeWin') and best.get('draw') and best.get('awayWin'):
            hw, dw, aw = best['homeWin'], best['draw'], best['awayWin']
            total = (1/hw) + (1/dw) + (1/aw)
            
            features['odds_implied_home'] = (1/hw) / total
            features['odds_implied_draw'] = (1/dw) / total
            features['odds_implied_away'] = (1/aw) / total
            features['odds_overround'] = total - 1.0
            
            # Movement
            if best.get('openingHomeWin') and best.get('isOpeningSet'):
                features['odds_movement_home'] = best['openingHomeWin'] - hw
                features['odds_movement_draw'] = (best.get('openingDraw') or dw) - dw
                features['odds_movement_away'] = (best.get('openingAwayWin') or aw) - aw
            else:
                features['odds_movement_home'] = 0.0
                features['odds_movement_draw'] = 0.0
                features['odds_movement_away'] = 0.0
        else:
            features['odds_implied_home'] = 0.33
            features['odds_implied_draw'] = 0.33
            features['odds_implied_away'] = 0.34
            features['odds_overround'] = 0.0
            features['odds_movement_home'] = 0.0
            features['odds_movement_draw'] = 0.0
            features['odds_movement_away'] = 0.0
        
        # Totals (Over/Under)
        totals = [o for o in odds if o.get('type') == 'totals' and o.get('handicap') == '2.5']
        if totals:
            t = totals[0]
            features['ou_25_over_implied'] = 1.0 / t['over'] if t.get('over') and t['over'] > 0 else 0.5
            features['ou_25_under_implied'] = 1.0 / t['under'] if t.get('under') and t['under'] > 0 else 0.5
            if t.get('openingOver') and t.get('isOpeningSet'):
                features['ou_movement'] = (t.get('openingOver') or t['over']) - t['over']
            else:
                features['ou_movement'] = 0.0
        else:
            features['ou_25_over_implied'] = 0.5
            features['ou_25_under_implied'] = 0.5
            features['ou_movement'] = 0.0
        
        # Asian Handicap
        spreads = [o for o in odds if o.get('type') == 'spreads']
        if spreads:
            features['ah_line'] = float(spreads[0].get('handicap', 0) or 0)
        else:
            features['ah_line'] = 0.0
        
        return features

    def _context_features(self, match: Dict) -> Dict[str, float]:
        """Match context features."""
        features = {}
        
        # Days since last match for each team
        for side, team_id in [('home', match['home_team_id']), ('away', match['away_team_id'])]:
            result = self.db.execute(text("""
                SELECT MAX("startTime") as last_match
                FROM "Match"
                WHERE ("homeTeamId" = :tid OR "awayTeamId" = :tid)
                  AND status = 'FT'
                  AND "startTime" < :match_time
            """), {'tid': team_id, 'match_time': match['start_time']}).fetchone()
            
            if result and result.last_match:
                delta = match['start_time'] - result.last_match
                features[f'{side}_days_rest'] = max(float(delta.days), 0)
            else:
                features[f'{side}_days_rest'] = 7.0  # Default
        
        features['rest_diff'] = features['home_days_rest'] - features['away_days_rest']
        
        return features

    @staticmethod
    def get_feature_names() -> List[str]:
        """Return ordered list of feature names for model training."""
        return [
            # Team Strength
            'elo_diff', 'fifa_rank_diff',
            'form_points_diff_5', 'form_points_diff_10',
            'avg_goals_scored_diff', 'avg_goals_conceded_diff',
            'home_avg_goals_scored_5', 'away_avg_goals_scored_5',
            'home_avg_goals_conceded_5', 'away_avg_goals_conceded_5',
            'home_win_rate', 'away_win_rate',
            'avg_yellow_cards_total', 'avg_corners_diff', 'avg_corners_total',
            'clean_sheet_rate_diff', 'btts_rate_avg',
            # H2H
            'h2h_home_win_rate', 'h2h_draw_rate', 'h2h_avg_total_goals', 'h2h_total_matches',
            # Odds
            'odds_implied_home', 'odds_implied_draw', 'odds_implied_away',
            'odds_overround',
            'odds_movement_home', 'odds_movement_draw', 'odds_movement_away',
            'ou_25_over_implied', 'ou_25_under_implied', 'ou_movement',
            'ah_line',
            # Context
            'home_days_rest', 'away_days_rest', 'rest_diff',
        ]
