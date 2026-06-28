"""
Odds Analysis Module.

Handles:
1. De-vigging (removing bookmaker margin) to extract true probabilities
2. Odds movement analysis (opening vs current)
3. Closing Line Value (CLV) calculation
4. Sharp money detection
"""
import numpy as np
from typing import Dict, List, Optional, Tuple


class OddsAnalyzer:
    """Analyze betting odds to extract market intelligence."""

    @staticmethod
    def de_vig_multiplicative(home_odds: float, draw_odds: float, away_odds: float) -> Dict[str, float]:
        """
        Remove bookmaker margin using the multiplicative (proportional) method.
        
        This is the simplest and most commonly used de-vigging method.
        Fair_prob(X) = implied_prob(X) / sum(all_implied_probs)
        
        Parameters
        ----------
        home_odds, draw_odds, away_odds : float
            Decimal odds for 1X2 market.
            
        Returns
        -------
        dict with fair probabilities and overround
        """
        if home_odds <= 1 or draw_odds <= 1 or away_odds <= 1:
            return {'home': 0.33, 'draw': 0.33, 'away': 0.34, 'overround': 0.0}
        
        # Implied probabilities (include margin)
        p_home = 1.0 / home_odds
        p_draw = 1.0 / draw_odds
        p_away = 1.0 / away_odds
        
        total = p_home + p_draw + p_away
        overround = total - 1.0  # Bookmaker margin
        
        # Fair probabilities (margin removed)
        fair_home = p_home / total
        fair_draw = p_draw / total
        fair_away = p_away / total
        
        return {
            'home': round(fair_home, 4),
            'draw': round(fair_draw, 4),
            'away': round(fair_away, 4),
            'overround': round(overround, 4),
        }

    @staticmethod
    def de_vig_power(home_odds: float, draw_odds: float, away_odds: float) -> Dict[str, float]:
        """
        Remove bookmaker margin using the Power method (Shin's method variant).
        
        More accurate than multiplicative for markets with heavy favorites.
        Uses an iterative approach to find the power parameter.
        """
        if home_odds <= 1 or draw_odds <= 1 or away_odds <= 1:
            return {'home': 0.33, 'draw': 0.33, 'away': 0.34, 'overround': 0.0}
        
        p_home = 1.0 / home_odds
        p_draw = 1.0 / draw_odds
        p_away = 1.0 / away_odds
        total = p_home + p_draw + p_away
        
        # Binary search for power parameter k such that sum(p_i^k) = 1
        lo, hi = 0.5, 2.0
        for _ in range(100):
            k = (lo + hi) / 2
            s = p_home**k + p_draw**k + p_away**k
            if s > 1.0:
                lo = k
            else:
                hi = k
        
        fair_home = p_home**k
        fair_draw = p_draw**k
        fair_away = p_away**k
        norm = fair_home + fair_draw + fair_away
        
        return {
            'home': round(fair_home / norm, 4),
            'draw': round(fair_draw / norm, 4),
            'away': round(fair_away / norm, 4),
            'overround': round(total - 1.0, 4),
        }

    @staticmethod
    def odds_movement(opening_odds: float, current_odds: float) -> Dict[str, float]:
        """
        Calculate odds movement metrics.
        
        Negative movement = odds shortened = more money coming in = market thinks more likely.
        Positive movement = odds drifted = less confidence.
        """
        if opening_odds <= 0 or current_odds <= 0:
            return {'absolute': 0.0, 'percentage': 0.0, 'direction': 'stable'}
        
        absolute = current_odds - opening_odds
        percentage = (current_odds - opening_odds) / opening_odds * 100
        
        if absolute < -0.05:
            direction = 'shortened'  # More money coming in
        elif absolute > 0.05:
            direction = 'drifted'  # Money moving away
        else:
            direction = 'stable'
        
        return {
            'absolute': round(absolute, 3),
            'percentage': round(percentage, 2),
            'direction': direction,
        }

    @staticmethod
    def calculate_clv(bet_odds: float, closing_odds: float) -> float:
        """
        Calculate Closing Line Value.
        
        CLV = (bet_odds / closing_odds) - 1
        
        Positive CLV = you got better odds than the closing line = long-term profitable.
        """
        if closing_odds <= 0:
            return 0.0
        return round((bet_odds / closing_odds) - 1.0, 4)

    @staticmethod
    def detect_sharp_movement(odds_history: List[Dict]) -> Dict:
        """
        Analyze odds history to detect sharp money movements.
        
        Sharp movement indicators:
        1. Large single move (>5% of implied probability)
        2. Consistent direction without reversal
        3. Movement against public sentiment
        """
        if len(odds_history) < 2:
            return {'is_sharp': False, 'confidence': 0.0, 'direction': 'none'}
        
        # Calculate total movement
        movements = []
        for i in range(1, len(odds_history)):
            old = odds_history[i-1]
            new = odds_history[i]
            
            if old.get('homeWin') and new.get('homeWin'):
                # Movement in implied probability space
                old_prob = 1.0 / old['homeWin']
                new_prob = 1.0 / new['homeWin']
                movements.append(new_prob - old_prob)
        
        if not movements:
            return {'is_sharp': False, 'confidence': 0.0, 'direction': 'none'}
        
        total_move = sum(movements)
        avg_move = total_move / len(movements)
        
        # Sharp if total movement > 3% in implied probability
        is_sharp = abs(total_move) > 0.03
        
        # Direction consistency (are all moves in the same direction?)
        if total_move > 0:
            same_dir = sum(1 for m in movements if m > 0)
        else:
            same_dir = sum(1 for m in movements if m < 0)
        consistency = same_dir / len(movements) if movements else 0
        
        direction = 'home' if total_move > 0.01 else ('away' if total_move < -0.01 else 'none')
        
        return {
            'is_sharp': is_sharp,
            'confidence': round(min(consistency, 1.0), 2),
            'direction': direction,
            'total_implied_prob_shift': round(total_move, 4),
            'num_movements': len(movements),
        }

    @staticmethod
    def analyze_match_odds(odds_data: List[Dict]) -> Dict:
        """
        Comprehensive odds analysis for a match.
        
        Aggregates odds from multiple bookmakers using Pinnacle as primary sharp source.
        """
        if not odds_data:
            return {
                'implied_probs': {'home': 0.33, 'draw': 0.33, 'away': 0.34},
                'movement': {},
                'sharp_signal': {'is_sharp': False},
            }
        
        # Priority: Pinnacle > Bet365 > Others
        h2h_odds = [o for o in odds_data if o.get('type') == 'h2h']
        
        # Find best sharp bookmaker
        pinnacle = next((o for o in h2h_odds if 'Pinnacle' in o.get('bookmaker', '')), None)
        best_odds = pinnacle or (h2h_odds[0] if h2h_odds else None)
        
        result = {
            'implied_probs': {'home': 0.33, 'draw': 0.33, 'away': 0.34},
            'movement': {},
            'overround': 0.0,
        }
        
        if best_odds and best_odds.get('homeWin') and best_odds.get('draw') and best_odds.get('awayWin'):
            # De-vig
            fair = OddsAnalyzer.de_vig_multiplicative(
                best_odds['homeWin'], best_odds['draw'], best_odds['awayWin']
            )
            result['implied_probs'] = {
                'home': fair['home'],
                'draw': fair['draw'],
                'away': fair['away'],
            }
            result['overround'] = fair['overround']
            
            # Movement analysis (if opening odds available)
            if best_odds.get('openingHomeWin'):
                result['movement'] = {
                    'home': OddsAnalyzer.odds_movement(best_odds['openingHomeWin'], best_odds['homeWin']),
                    'draw': OddsAnalyzer.odds_movement(best_odds['openingDraw'], best_odds['draw']),
                    'away': OddsAnalyzer.odds_movement(best_odds['openingAwayWin'], best_odds['awayWin']),
                }
        
        return result
