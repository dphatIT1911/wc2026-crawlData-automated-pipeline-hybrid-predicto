import React, { useEffect, useState } from 'react';
import { ColorBlock } from '../../components/ColorBlock/ColorBlock';
import { Button } from '../../components/Button/Button';
import './Predictions.css';

import { API_URL } from '../../config';

interface Prediction {
  matchId: number;
  homeTeam: string;
  awayTeam: string;
  prediction?: {
    home_win_probability: number;
    draw_probability: number;
    away_win_probability: number;
    predicted_score: string;
    score_probability: number;
    asian_handicap: string;
    over_under_line: number;
    over_probability: number;
    under_probability: number;
    yellow_cards_prediction: number;
    corners_prediction: number;
    btts_probability: number;
    confidence: number;
    model_version: string;
  };
  value_bet?: {
    recommendation: string | null;
    edge: number;
    kelly_fraction?: number;
  };
  error?: string;
}

export const Predictions: React.FC = () => {
  const [data, setData] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/prediction/upcoming`)
      .then(res => res.json())
      .then(json => {
        setData(json.predictions || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="predictions-page">
      <ColorBlock color="mint">
        <h1 style={{ 
          fontSize: 'var(--typography-display-lg-size)',
          fontWeight: 'var(--typography-display-lg-weight)',
          letterSpacing: 'var(--typography-display-lg-letter-spacing)',
          lineHeight: 'var(--typography-display-lg-line-height)',
          marginBottom: 'var(--spacing-md)'
        }}>
          AI Match Predictions
        </h1>
        <p style={{ 
          fontSize: 'var(--typography-body-lg-size)',
          marginBottom: 'var(--spacing-xl)',
          maxWidth: '800px'
        }}>
          Dữ liệu trực tiếp từ Hybrid Engine. Hệ thống đang phân tích các trận đấu sắp tới dựa trên CatBoost và sức mạnh đội bóng (Dixon-Coles).
        </p>
      </ColorBlock>

      <div className="predictions-list">
        {loading ? (
          <div className="loading-state">Đang tải dữ liệu AI...</div>
        ) : data.length === 0 ? (
          <div className="empty-state">Không có trận đấu nào sắp tới.</div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Trận đấu</th>
                  <th>Dự đoán (1X2)</th>
                  <th>Value Bets (Kelly)</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {data.map((match, idx) => (
                  <tr key={match.matchId || idx}>
                    <td>
                      <div className="match-title">
                        {match.homeTeam} vs {match.awayTeam}
                      </div>
                    </td>
                    <td>
                      {match.error ? (
                        <span className="error-text">Lỗi: {match.error}</span>
                      ) : (
                        <div className="prediction-probs">
                          Home: {match.prediction ? (match.prediction.home_win_probability * 100).toFixed(1) : '0.0'}% <br/>
                          Draw: {match.prediction ? (match.prediction.draw_probability * 100).toFixed(1) : '0.0'}% <br/>
                          Away: {match.prediction ? (match.prediction.away_win_probability * 100).toFixed(1) : '0.0'}%
                        </div>
                      )}
                    </td>
                    <td>
                      {match.value_bet && match.value_bet.recommendation ? (
                        <div className="value-bets">
                          <span className="badge badge-success">
                            {match.value_bet.recommendation}: Kelly {((match.value_bet.kelly_fraction || 0) * 100).toFixed(2)}%
                          </span>
                        </div>
                      ) : (
                        <span className="badge badge-neutral">Không có Value Bet</span>
                      )}
                    </td>
                    <td>
                      <Button variant="secondary">Chi tiết</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
