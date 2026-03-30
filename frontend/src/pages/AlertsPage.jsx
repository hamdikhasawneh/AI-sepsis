import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';

export default function AlertsPage() {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState([]);
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAlerts();
  }, [showUnreadOnly]);

  const loadAlerts = async () => {
    try {
      const res = await api.get('/alerts/', { params: { unread_only: showUnreadOnly } });
      setAlerts(res.data);
    } catch (err) {
      console.error('Failed to load alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (alertId) => {
    try {
      await api.patch(`/alerts/${alertId}/read`);
      loadAlerts();
    } catch (err) {
      console.error('Failed to mark alert as read:', err);
    }
  };

  if (loading) return <div className="loading">Loading alerts...</div>;

  return (
    <div className="alerts-page">
      <div className="page-header">
        <h1>🔔 Alerts</h1>
        <div className="page-actions">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showUnreadOnly}
              onChange={(e) => setShowUnreadOnly(e.target.checked)}
            />
            Show unread only
          </label>
        </div>
      </div>

      {alerts.length === 0 ? (
        <div className="empty-state">
          <p>{showUnreadOnly ? 'No unread alerts.' : 'No alerts found.'}</p>
        </div>
      ) : (
        <div className="alerts-list">
          {alerts.map((alert) => (
            <div
              key={alert.alert_id}
              className={`alert-card ${alert.is_read ? 'alert-read' : 'alert-unread'} alert-level-${alert.alert_level}`}
            >
              <div className="alert-card-header">
                <div className="alert-card-left">
                  <span className={`alert-level-badge level-${alert.alert_level}`}>
                    {alert.alert_level === 'critical' ? '🔴' : '🟠'} {alert.alert_level}
                  </span>
                  <span className="alert-patient-name">{alert.patient_name}</span>
                </div>
                <div className="alert-card-right">
                  <span className="alert-time">
                    {alert.created_at ? new Date(alert.created_at).toLocaleString() : ''}
                  </span>
                  {alert.is_read ? (
                    <span className="alert-read-badge">
                      ✓ Read by {alert.read_by_name}
                    </span>
                  ) : (
                    user.role === 'doctor' && (
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => handleMarkRead(alert.alert_id)}
                      >
                        Mark as Read
                      </button>
                    )
                  )}
                </div>
              </div>
              <div className="alert-card-body">
                <p>{alert.alert_message}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {user.role === 'nurse' && (
        <div className="alert-info-banner">
          <p>ℹ️ As a nurse, you can view alerts but only doctors can mark them as read.</p>
        </div>
      )}
    </div>
  );
}
