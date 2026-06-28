import React, { useEffect, useState } from 'react';
import { ColorBlock } from '../../components/ColorBlock/ColorBlock';
import { Button } from '../../components/Button/Button';
import './CrawlerData.css';
import { API_URL } from '../../config';

const API = API_URL;

interface Match {
  id: number;
  startTime: string;
  status: string;
  homeTeam: { name: string };
  awayTeam: { name: string };
  fixtureId: number;
}

export const CrawlerData: React.FC = () => {
  const [data, setData] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/matches`)
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

  const handleRunCrawler = () => {
    alert("Kích hoạt Crawler thành công. Đang chạy ngầm...");
    fetch(`${API}/crawler/run`).catch(console.error);
  };

  return (
    <div className="crawler-page">
      <ColorBlock color="lime">
        <h1 style={{ 
          fontSize: 'var(--typography-display-lg-size)',
          fontWeight: 'var(--typography-display-lg-weight)',
          marginBottom: 'var(--spacing-md)'
        }}>
          Crawler Data Hub
        </h1>
        <p style={{ marginBottom: 'var(--spacing-xl)' }}>
          Dữ liệu được tự động cào từ API-Football và The Odds API. Bạn có thể kích hoạt cào dữ liệu thủ công bằng nút bên dưới.
        </p>
        <Button variant="primary" onClick={handleRunCrawler}>Force Run Crawler</Button>
      </ColorBlock>

      <div className="crawler-list" style={{ marginTop: 'var(--spacing-xl)' }}>
        {loading ? (
          <div className="loading-state">Đang tải dữ liệu Crawler...</div>
        ) : data.length === 0 ? (
          <div className="empty-state">Chưa có dữ liệu thô.</div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID Trận</th>
                  <th>API-Football Fixture ID</th>
                  <th>Trận đấu</th>
                  <th>Thời gian (UTC)</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {data.slice(0, 50).map(match => (
                  <tr key={match.id}>
                    <td>#{match.id}</td>
                    <td><span className="badge badge-neutral">{match.fixtureId}</span></td>
                    <td>
                      <span className="match-title">{match.homeTeam?.name} vs {match.awayTeam?.name}</span>
                    </td>
                    <td>{new Date(match.startTime).toLocaleString('vi-VN')}</td>
                    <td>
                      <span className={`badge ${match.status === 'NS' ? 'badge-success' : 'badge-neutral'}`}>
                        {match.status}
                      </span>
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
