import React, { useEffect, useState } from 'react';
import { ColorBlock } from '../../components/ColorBlock/ColorBlock';
import { Button } from '../../components/Button/Button';
import { API_URL } from '../../config';
import './Settings.css';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{text: string, type: 'success'|'error'} | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/settings`)
      .then(res => res.json())
      .then(data => {
        setSettings(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handleChange = (key: string, value: string) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (!res.ok) throw new Error('Lỗi khi lưu cấu hình');
      const data = await res.json();
      setSettings(data);
      setMessage({ text: 'Lưu cấu hình thành công', type: 'success' });
    } catch (err: any) {
      setMessage({ text: err.message, type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="settings-page"><div className="loading-state">Đang tải...</div></div>;
  }

  return (
    <div className="settings-page">
      <ColorBlock color="salmon">
        <h1>Cấu hình Hệ thống</h1>
        <p>Quản lý Scheduler, API Keys và cấu hình chung.</p>
      </ColorBlock>

      <div className="section-card mt-xl">
        <div className="settings-form">
          <div className="form-group">
            <label>API Football Key</label>
            <input 
              type="text" 
              value={settings['API_FOOTBALL_KEY'] || ''} 
              onChange={e => handleChange('API_FOOTBALL_KEY', e.target.value)} 
              placeholder="Nhập API Key..."
            />
          </div>
          
          <div className="form-group">
            <label>The Odds API Key</label>
            <input 
              type="text" 
              value={settings['THE_ODDS_API_KEY'] || ''} 
              onChange={e => handleChange('THE_ODDS_API_KEY', e.target.value)} 
              placeholder="Nhập API Key..."
            />
          </div>

          <div className="form-group">
            <label>Crawler Cron Schedule</label>
            <input 
              type="text" 
              value={settings['CRAWLER_CRON'] || '0 3,12,18,21 * * *'} 
              onChange={e => handleChange('CRAWLER_CRON', e.target.value)} 
            />
            <small className="help-text">Định dạng Cron expression. Mặc định: 4 lần / ngày.</small>
          </div>

          {message && (
            <div className={`message-box ${message.type}`}>
              {message.text}
            </div>
          )}

          <div className="form-actions">
            <Button onClick={handleSave} disabled={saving}>
              {saving ? 'Đang lưu...' : 'Lưu Thay Đổi'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
