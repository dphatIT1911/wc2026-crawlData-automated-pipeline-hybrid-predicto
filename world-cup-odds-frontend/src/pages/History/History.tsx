import React, { useEffect, useState } from 'react';
import { ColorBlock } from '../../components/ColorBlock/ColorBlock';
import { API_URL } from '../../config';
import './History.css';

interface CrawlerLog {
  id: number;
  runAt: string;
  status: string;
  matches: number;
  odds: number;
  changes: number;
  error: string | null;
}

export const History: React.FC = () => {
  const [logs, setLogs] = useState<CrawlerLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/history/crawler`)
      .then(res => res.json())
      .then(data => {
        setLogs(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const formatDate = (dt: string) => {
    return new Date(dt).toLocaleString('vi-VN');
  };

  return (
    <div className="history-page">
      <ColorBlock color="purple">
        <h1>Lịch sử Hệ thống</h1>
        <p>Theo dõi các tiến trình Crawler, thay đổi Odds và lịch sử dự đoán.</p>
      </ColorBlock>

      <div className="section-card mt-xl">
        <div className="section-header">
          <h2 className="section-title">Crawler Logs (Gần nhất)</h2>
        </div>
        {loading ? (
          <div className="loading-state">Đang tải lịch sử...</div>
        ) : logs.length === 0 ? (
          <div className="empty-state">Chưa có lịch sử Crawler.</div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Thời gian</th>
                  <th>Trạng thái</th>
                  <th>Trận đấu</th>
                  <th>Odds xử lý</th>
                  <th>Thay đổi Odds</th>
                  <th>Lỗi</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id}>
                    <td className="cell-date">{formatDate(log.runAt)}</td>
                    <td>
                      <span className={`badge ${log.status === 'SUCCESS' ? 'badge-success' : 'badge-danger'}`}>
                        {log.status}
                      </span>
                    </td>
                    <td>{log.matches}</td>
                    <td>{log.odds}</td>
                    <td>{log.changes}</td>
                    <td className="error-text">{log.error || '-'}</td>
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
