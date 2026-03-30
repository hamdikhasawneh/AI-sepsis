import { useState, useEffect } from 'react';
import api from '../api/client';

export default function AdminSettingsPage() {
  const [threshold, setThreshold] = useState('');
  const [settings, setSettings] = useState([]);
  const [simulatorStatus, setSimulatorStatus] = useState({ running: false, interval_seconds: 60 });
  const [interval, setInterval] = useState('60');
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [thresholdRes, settingsRes, simStatusRes] = await Promise.all([
        api.get('/settings/threshold'),
        api.get('/settings/'),
        api.get('/vitals/simulator/status').catch(() => ({ data: { running: false, interval_seconds: 60 } })),
      ]);
      setThreshold(thresholdRes.data.value);
      setSettings(settingsRes.data);
      setSimulatorStatus(simStatusRes.data);
      setInterval(String(simStatusRes.data.interval_seconds));
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const updateThreshold = async () => {
    setMessage('');
    try {
      await api.put('/settings/threshold', { value: threshold });
      setMessage('✓ Threshold updated successfully');
      loadData();
    } catch (err) {
      setMessage('✗ ' + (err.response?.data?.detail || 'Failed to update'));
    }
  };

  const toggleSimulator = async () => {
    setMessage('');
    try {
      if (simulatorStatus.running) {
        await api.post('/vitals/simulator/stop');
        setMessage('✓ Simulator stopped');
      } else {
        await api.post('/vitals/simulator/start');
        setMessage('✓ Simulator started');
      }
      loadData();
    } catch (err) {
      setMessage('✗ ' + (err.response?.data?.detail || 'Failed'));
    }
  };

  const updateInterval = async () => {
    setMessage('');
    try {
      await api.put('/vitals/simulator/interval', null, { params: { interval: parseInt(interval) } });
      setMessage('✓ Interval updated');
      loadData();
    } catch (err) {
      setMessage('✗ ' + (err.response?.data?.detail || 'Failed'));
    }
  };

  const triggerSimulation = async () => {
    setMessage('');
    try {
      const res = await api.post('/vitals/simulate');
      setMessage('✓ ' + res.data.message);
    } catch (err) {
      setMessage('✗ ' + (err.response?.data?.detail || 'Failed'));
    }
  };

  if (loading) return <div className="loading">Loading settings...</div>;

  return (
    <div className="admin-settings-page">
      <div className="page-header">
        <h1>⚙️ System Settings</h1>
      </div>

      {message && (
        <div className={`alert ${message.startsWith('✓') ? 'alert-success' : 'alert-error'}`}>
          {message}
        </div>
      )}

      {/* Alert Threshold */}
      <div className="settings-section">
        <div className="info-card">
          <h3>🎯 Alert Threshold</h3>
          <p className="settings-desc">
            Predictions with risk scores above this threshold will trigger alerts.
            Default: 0.80 (80%)
          </p>
          <div className="settings-inline">
            <input
              type="number"
              step="0.01"
              min="0.01"
              max="0.99"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              className="settings-input"
            />
            <button className="btn btn-primary" onClick={updateThreshold}>
              Update Threshold
            </button>
          </div>
          <p className="settings-hint">
            Current: <strong>{(parseFloat(threshold) * 100).toFixed(0)}%</strong> risk score
          </p>
        </div>
      </div>

      {/* Simulator Controls */}
      <div className="settings-section">
        <div className="info-card">
          <h3>🔄 Vital Signs Simulator</h3>
          <p className="settings-desc">
            The simulator generates mock vital signs for all admitted patients at a configurable interval,
            runs predictions, and creates alerts when thresholds are exceeded.
          </p>

          <div className="simulator-status">
            <span className={`sim-indicator ${simulatorStatus.running ? 'sim-running' : 'sim-stopped'}`}>
              {simulatorStatus.running ? '● Running' : '○ Stopped'}
            </span>
            <span className="sim-interval">
              Interval: {simulatorStatus.interval_seconds}s
            </span>
          </div>

          <div className="settings-controls">
            <div className="settings-inline">
              <button
                className={`btn ${simulatorStatus.running ? 'btn-danger' : 'btn-primary'}`}
                onClick={toggleSimulator}
              >
                {simulatorStatus.running ? '⏹ Stop Simulator' : '▶ Start Simulator'}
              </button>
              <button className="btn btn-secondary" onClick={triggerSimulation}>
                ⚡ Run Once
              </button>
            </div>

            <div className="settings-inline" style={{ marginTop: '12px' }}>
              <label>Interval (seconds):</label>
              <input
                type="number"
                min="10"
                max="600"
                value={interval}
                onChange={(e) => setInterval(e.target.value)}
                className="settings-input"
                style={{ width: '100px' }}
              />
              <button className="btn btn-secondary" onClick={updateInterval}>
                Set Interval
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* All Settings Table */}
      <div className="settings-section">
        <div className="info-card">
          <h3>📋 All Settings</h3>
          <div className="table-container" style={{ border: 'none' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Key</th>
                  <th>Value</th>
                  <th>Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {settings.map((s, idx) => (
                  <tr key={idx}>
                    <td><code>{s.key}</code></td>
                    <td>{s.value}</td>
                    <td>{s.updated_at ? new Date(s.updated_at).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
