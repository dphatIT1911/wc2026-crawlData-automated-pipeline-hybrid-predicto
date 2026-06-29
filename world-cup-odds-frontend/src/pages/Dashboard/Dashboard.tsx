import React, { useEffect, useState } from 'react';
import './Dashboard.css';
import { API_URL } from '../../config';

const API = API_URL;

interface Team {
  id: number;
  name: string;
  flagUrl?: string;
}

interface Match {
  id: number;
  startTime: string;
  status: string;
  homeScore: number | null;
  awayScore: number | null;
  homeTeam: Team;
  awayTeam: Team;
}

interface Stats {
  total: number;
  upcoming: number;
  live: number;
  finished: number;
  teams: number;
}

export const Dashboard: React.FC = () => {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/matches`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        setMatches(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setError('Không thể kết nối đến Backend. Kiểm tra NestJS đang chạy ở port 3000.');
        setLoading(false);
      });
  }, []);

  const stats: Stats = {
    total: matches.length,
    upcoming: matches.filter(m => m.status === 'NS').length,
    live: matches.filter(m => m.status === 'LIVE' || m.status === 'HT').length,
    finished: matches.filter(m => m.status === 'FT').length,
    teams: [...new Set(matches.flatMap(m => [m.homeTeam?.id, m.awayTeam?.id]))].length,
  };

  const upcomingMatches = matches
    .filter(m => m.status === 'NS')
    .slice(0, 8);

  const formatDate = (dt: string) => {
    const d = new Date(dt);
    return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' }) +
      ' ' + d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  };

  const statusBadge = (s: string) => {
    if (s === 'NS') return <span className="badge badge-upcoming">Sắp diễn ra</span>;
    if (s === 'FT') return <span className="badge badge-finished">Kết thúc</span>;
    if (s === 'LIVE' || s === 'HT') return <span className="badge badge-live">🔴 Trực tiếp</span>;
    return <span className="badge">{s}</span>;
  };

  return (
    <div className="dashboard-page">
      {/* Hero */}
      <div className="dashboard-hero">
        <div className="hero-content">
          <div className="hero-tag">⚽ World Cup 2026 — AI Prediction Engine</div>
          <h1 className="hero-title">Phân tích & Dự đoán<br />Bóng đá Thông minh</h1>
          <p className="hero-desc">
            Kết hợp CatBoost + Dixon-Coles + Kelly Criterion để tìm kiếm value bets có lợi nhuận cao nhất.
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card stat-blue">
          <div className="stat-icon">📋</div>
          <div className="stat-value">{loading ? '...' : stats.total}</div>
          <div className="stat-label">Tổng trận đấu</div>
        </div>
        <div className="stat-card stat-green">
          <div className="stat-icon">⏳</div>
          <div className="stat-value">{loading ? '...' : stats.upcoming}</div>
          <div className="stat-label">Trận sắp tới</div>
        </div>
        <div className="stat-card stat-red">
          <div className="stat-icon">🔴</div>
          <div className="stat-value">{loading ? '...' : stats.live}</div>
          <div className="stat-label">Đang diễn ra</div>
        </div>
        <div className="stat-card stat-purple">
          <div className="stat-icon">🏆</div>
          <div className="stat-value">{loading ? '...' : stats.teams}</div>
          <div className="stat-label">Đội bóng</div>
        </div>
      </div>

      {/* Upcoming Matches Table */}
      <div className="section-card">
        <div className="section-header">
          <h2 className="section-title">Trận đấu sắp tới</h2>
          <span className="section-count">{stats.upcoming} trận</span>
        </div>

        {loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <span>Đang tải dữ liệu từ database...</span>
          </div>
        ) : error ? (
          <div className="error-state">
            <div className="error-icon">⚠️</div>
            <p>{error}</p>
            <code>GET {API_URL}/matches</code>
          </div>
        ) : upcomingMatches.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📭</div>
            <p>Không có trận đấu sắp tới trong database.</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Thời gian</th>
                  <th>Trận đấu</th>
                  <th>Trạng thái</th>
                  <th>Tỷ số</th>
                </tr>
              </thead>
              <tbody>
                {upcomingMatches.map((m, idx) => (
                  <tr key={m.id}>
                    <td className="cell-num">{idx + 1}</td>
                    <td className="cell-date">{formatDate(m.startTime)}</td>
                    <td className="cell-match">
                      <span className="team-name">{m.homeTeam?.name ?? '?'}</span>
                      <span className="vs-divider">vs</span>
                      <span className="team-name">{m.awayTeam?.name ?? '?'}</span>
                    </td>
                    <td>{statusBadge(m.status)}</td>
                    <td className="cell-score">
                      {m.homeScore != null && m.awayScore != null
                        ? `${m.homeScore} - ${m.awayScore}`
                        : '— : —'}
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
