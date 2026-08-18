import React, { useEffect, useState } from 'react';
import { ColorBlock } from '../../components/ColorBlock/ColorBlock';
import { API_URL } from '../../config';
import './Analytics.css';

interface AnalyticsData {
  overview: {
    totalMatches: number;
    upcoming: number;
    finished: number;
    live: number;
  };
  goals: {
    totalGoals: number;
    avgGoals: number;
  };
  aiPerformance?: {
    accuracy: number;
    brierScore: number;
    roiSimulated: number;
    winRate: number;
  };
}

export const Analytics: React.FC = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/analytics/dashboard`)
      .then(res => res.json())
      .then(json => {
        setData(json);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="analytics-page">
      <ColorBlock color="blue">
        <h1>Analytics & Insights</h1>
        <p>Thống kê hiệu suất toàn hệ thống, tỉ lệ bàn thắng và hiệu suất của AI Model.</p>
      </ColorBlock>
      
      {loading ? (
        <div className="loading-state">Đang tải dữ liệu phân tích...</div>
      ) : data ? (
        <div className="analytics-grid">
          <div className="analytics-card">
            <h3>Tổng quan trận đấu</h3>
            <p>Đã kết thúc: {data.overview.finished}</p>
            <p>Sắp tới: {data.overview.upcoming}</p>
            <p>Đang diễn ra: {data.overview.live}</p>
          </div>
          
          <div className="analytics-card">
            <h3>Thống kê bàn thắng</h3>
            <p>Tổng bàn thắng: {data.goals.totalGoals}</p>
            <p>Trung bình / Trận: {data.goals.avgGoals}</p>
          </div>

          <div className="analytics-card">
            <h3>Hiệu suất AI Model</h3>
            {data.aiPerformance ? (
              <>
                <p>Accuracy: {(data.aiPerformance.accuracy * 100).toFixed(2)}%</p>
                <p>Brier Score: {data.aiPerformance.brierScore.toFixed(4)}</p>
                <p>Simulated ROI: {(data.aiPerformance.roiSimulated * 100).toFixed(2)}%</p>
                <p>Win Rate: {(data.aiPerformance.winRate * 100).toFixed(2)}%</p>
              </>
            ) : (
              <p>Chưa có dữ liệu đánh giá model (ModelMetrics).</p>
            )}
          </div>
        </div>
      ) : (
        <div className="empty-state">Không thể tải dữ liệu phân tích.</div>
      )}
    </div>
  );
};
