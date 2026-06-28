"""
Dixon-Coles Model Implementation.

Based on the paper: "Modelling Association Football Scores and Inefficiencies 
in the Football Betting Market" by Mark Dixon & Stuart Coles (1997).

This model:
1. Estimates attack/defense parameters for each team via MLE
2. Applies a correlation correction (rho) for low-scoring draws
3. Uses time-decay weighting to prioritize recent matches
4. Generates a full score probability matrix for any match
"""
import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson
from typing import Dict, List, Tuple, Optional
import warnings

warnings.filterwarnings("ignore")


class DixonColesModel:
    """
    Dixon-Coles bivariate Poisson model for football score prediction.
    
    Parameters
    ----------
    xi : float
        Time decay parameter. Higher = more weight on recent matches.
        Typical range: 0.001 - 0.01. Default 0.005 (~6 months half-life).
    """

    def __init__(self, xi: float = 0.005):
        self.xi = xi
        self.params: Optional[Dict[str, float]] = None
        self.teams: List[str] = []
        self._fitted = False

    @staticmethod
    def tau(x: int, y: int, lambda_x: float, mu_y: float, rho: float) -> float:
        """
        Dixon-Coles correction factor for low scores.
        
        Adjusts probabilities for scores (0,0), (1,0), (0,1), (1,1)
        to account for correlation between home and away goals.
        """
        if x == 0 and y == 0:
            return 1.0 - lambda_x * mu_y * rho
        elif x == 0 and y == 1:
            return 1.0 + lambda_x * rho
        elif x == 1 and y == 0:
            return 1.0 + mu_y * rho
        elif x == 1 and y == 1:
            return 1.0 - rho
        else:
            return 1.0

    @staticmethod
    def score_probability(x: int, y: int, lambda_x: float, mu_y: float, rho: float) -> float:
        """
        Calculate P(HomeGoals=x, AwayGoals=y) using Dixon-Coles model.
        """
        tau = DixonColesModel.tau(x, y, lambda_x, mu_y, rho)
        p = tau * poisson.pmf(x, lambda_x) * poisson.pmf(y, mu_y)
        return max(p, 1e-10)  # Avoid zero probabilities

    def _build_score_matrix(self, lambda_x: float, mu_y: float, rho: float, 
                            max_goals: int = 8) -> np.ndarray:
        """
        Build full score probability matrix P(i, j) for i, j in [0, max_goals].
        """
        matrix = np.zeros((max_goals + 1, max_goals + 1))
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                matrix[i][j] = self.score_probability(i, j, lambda_x, mu_y, rho)
        
        # Normalize to ensure probabilities sum to 1
        matrix /= matrix.sum()
        return matrix

    def _time_weight(self, days_ago: float) -> float:
        """
        Exponential time-decay weight. Recent matches get higher weight.
        
        w(t) = exp(-xi * t)
        """
        return np.exp(-self.xi * days_ago)

    def _neg_log_likelihood(self, params: np.ndarray, 
                            home_teams: List[str], away_teams: List[str],
                            home_goals: List[int], away_goals: List[int],
                            weights: List[float]) -> float:
        """
        Negative log-likelihood for the Dixon-Coles model.
        
        Parameters are organized as:
        [attack_1, ..., attack_n, defense_1, ..., defense_n, home_advantage, rho]
        """
        n_teams = len(self.teams)
        
        # Extract parameters
        attack = dict(zip(self.teams, params[:n_teams]))
        defense = dict(zip(self.teams, params[n_teams:2*n_teams]))
        home_adv = params[2 * n_teams]
        rho = params[2 * n_teams + 1]
        
        log_likelihood = 0.0
        
        for i in range(len(home_teams)):
            ht = home_teams[i]
            at = away_teams[i]
            hg = home_goals[i]
            ag = away_goals[i]
            w = weights[i]
            
            # Expected goals
            lambda_x = np.exp(attack[ht] + defense[at] + home_adv)
            mu_y = np.exp(attack[at] + defense[ht])
            
            # Clamp to avoid numerical issues
            lambda_x = np.clip(lambda_x, 0.01, 10.0)
            mu_y = np.clip(mu_y, 0.01, 10.0)
            
            # Log probability with Dixon-Coles correction
            p = self.score_probability(hg, ag, lambda_x, mu_y, rho)
            log_likelihood += w * np.log(max(p, 1e-10))
        
        return -log_likelihood

    def fit(self, home_teams: List[str], away_teams: List[str],
            home_goals: List[int], away_goals: List[int],
            days_ago: Optional[List[float]] = None) -> 'DixonColesModel':
        """
        Fit the Dixon-Coles model using Maximum Likelihood Estimation.
        
        Parameters
        ----------
        home_teams : list of str
        away_teams : list of str
        home_goals : list of int
        away_goals : list of int
        days_ago : list of float, optional
            Days since each match. Used for time-decay weighting.
        """
        # Build team list
        all_teams = set(home_teams) | set(away_teams)
        self.teams = sorted(list(all_teams))
        n_teams = len(self.teams)
        
        if n_teams < 2:
            raise ValueError("Need at least 2 teams to fit the model")
        
        # Compute weights
        if days_ago is not None:
            weights = [self._time_weight(d) for d in days_ago]
        else:
            weights = [1.0] * len(home_teams)
        
        # Initial parameters: attack=0, defense=0, home_adv=0.25, rho=-0.05
        x0 = np.zeros(2 * n_teams + 2)
        x0[2 * n_teams] = 0.25      # home advantage
        x0[2 * n_teams + 1] = -0.05  # rho (negative = fewer low-scoring draws)
        
        # Constraints: sum of attack params = 0 (identifiability)
        constraints = [{
            'type': 'eq',
            'fun': lambda p: np.sum(p[:n_teams])  # Sum of attacks = 0
        }]
        
        # Bounds for rho: (-1, 1)
        bounds = [(None, None)] * (2 * n_teams)  # attack & defense: unbounded
        bounds.append((None, None))  # home advantage: unbounded
        bounds.append((-0.99, 0.99))  # rho: bounded
        
        # Optimize
        result = minimize(
            self._neg_log_likelihood,
            x0,
            args=(home_teams, away_teams, home_goals, away_goals, weights),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000, 'ftol': 1e-8}
        )
        
        if not result.success:
            # Try L-BFGS-B without constraint (use regularization instead)
            result = minimize(
                self._neg_log_likelihood,
                x0,
                args=(home_teams, away_teams, home_goals, away_goals, weights),
                method='L-BFGS-B',
                bounds=bounds,
                options={'maxiter': 1000}
            )
        
        # Store parameters
        self.params = {
            'attack': dict(zip(self.teams, result.x[:n_teams])),
            'defense': dict(zip(self.teams, result.x[n_teams:2*n_teams])),
            'home_advantage': result.x[2 * n_teams],
            'rho': result.x[2 * n_teams + 1],
        }
        self._fitted = True
        
        return self

    def predict_score_matrix(self, home_team: str, away_team: str, 
                              max_goals: int = 8) -> np.ndarray:
        """
        Generate score probability matrix for a given match.
        
        Returns
        -------
        np.ndarray of shape (max_goals+1, max_goals+1)
            matrix[i][j] = P(HomeGoals=i, AwayGoals=j)
        """
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        
        attack = self.params['attack']
        defense = self.params['defense']
        home_adv = self.params['home_advantage']
        rho = self.params['rho']
        
        # Use average params for unknown teams
        avg_attack = np.mean(list(attack.values()))
        avg_defense = np.mean(list(defense.values()))
        
        att_h = attack.get(home_team, avg_attack)
        def_h = defense.get(home_team, avg_defense)
        att_a = attack.get(away_team, avg_attack)
        def_a = defense.get(away_team, avg_defense)
        
        lambda_x = np.exp(att_h + def_a + home_adv)
        mu_y = np.exp(att_a + def_h)
        
        # Clamp
        lambda_x = np.clip(lambda_x, 0.1, 8.0)
        mu_y = np.clip(mu_y, 0.1, 8.0)
        
        return self._build_score_matrix(lambda_x, mu_y, rho, max_goals)

    def predict(self, home_team: str, away_team: str) -> Dict:
        """
        Full prediction for a match.
        
        Returns dict with:
        - home_win_prob, draw_prob, away_win_prob
        - predicted_score, score_probability
        - expected_home_goals, expected_away_goals
        - over_under probabilities
        - btts_prob
        """
        matrix = self.predict_score_matrix(home_team, away_team)
        max_goals = matrix.shape[0]
        
        # 1X2 probabilities
        home_win = sum(matrix[i][j] for i in range(max_goals) for j in range(max_goals) if i > j)
        draw = sum(matrix[i][i] for i in range(max_goals))
        away_win = sum(matrix[i][j] for i in range(max_goals) for j in range(max_goals) if i < j)
        
        # Normalize
        total = home_win + draw + away_win
        home_win /= total
        draw /= total
        away_win /= total
        
        # Most likely score
        best_i, best_j = np.unravel_index(matrix.argmax(), matrix.shape)
        
        # Expected goals
        exp_home = sum(i * matrix[i].sum() for i in range(max_goals))
        exp_away = sum(j * matrix[:, j].sum() for j in range(max_goals))
        
        # Over/Under
        over_under = {}
        for line in [1.5, 2.5, 3.5]:
            over = sum(matrix[i][j] for i in range(max_goals) for j in range(max_goals) if i + j > line)
            under = 1.0 - over
            over_under[f"over_{line}"] = round(over, 4)
            over_under[f"under_{line}"] = round(under, 4)
        
        # BTTS
        btts = sum(matrix[i][j] for i in range(1, max_goals) for j in range(1, max_goals))
        
        return {
            'home_win_prob': round(home_win, 4),
            'draw_prob': round(draw, 4),
            'away_win_prob': round(away_win, 4),
            'predicted_home_score': int(best_i),
            'predicted_away_score': int(best_j),
            'score_probability': round(float(matrix[best_i][best_j]), 4),
            'expected_home_goals': round(float(exp_home), 2),
            'expected_away_goals': round(float(exp_away), 2),
            'btts_prob': round(float(btts), 4),
            **over_under,
        }

    def get_team_strengths(self) -> Dict:
        """Return attack and defense ratings for all teams."""
        if not self._fitted:
            return {}
        return {
            team: {
                'attack': round(self.params['attack'][team], 4),
                'defense': round(self.params['defense'][team], 4),
            }
            for team in self.teams
        }
