import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';

export default function DashboardPage() {
  const { user } = useAuth();
  const [patients, setPatients] = useState([]);
  const [unreadAlerts, setUnreadAlerts] = useState(0);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [simulatorStatus, setSimulatorStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
    // Refresh alerts every 30 seconds
    const interval = setInterval(() => {
      api.get('/alerts/unread/count').then(r => setUnreadAlerts(r.data.unread_count)).catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboard = async () => {
    try {
      const [patientsRes, alertCountRes, alertsRes] = await Promise.all([
        api.get('/patients/', { params: { status_filter: 'active' } }),
        api.get('/alerts/unread/count'),
        api.get('/alerts/', { params: { unread_only: true } }),
      ]);
      setPatients(patientsRes.data);
      setUnreadAlerts(alertCountRes.data.unread_count);
      setRecentAlerts(alertsRes.data.slice(0, 5));

      if (user.role === 'admin') {
        try {
          const simRes = await api.get('/vitals/simulator/status');
          setSimulatorStatus(simRes.data);
        } catch {}
      }
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleSimulator = async () => {
    try {
      if (simulatorStatus?.running) {
        await api.post('/vitals/simulator/stop');
      } else {
        await api.post('/vitals/simulator/start');
      }
      const simRes = await api.get('/vitals/simulator/status');
      setSimulatorStatus(simRes.data);
    } catch (err) {
      console.error('Simulator toggle failed:', err);
    }
  };

  if (loading) return <div className="loading">Loading dashboard...</div>;

  return (
    <div className="dashboard">
      <div className="page-header">
        <h1>
          {user.role === 'doctor' ? '👨‍⚕️ Doctor' : user.role === 'nurse' ? '👩‍⚕️ Nurse' : '⚙️ Admin'} Dashboard
        </h1>
        <p>Welcome back, {user.full_name}</p>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-number">{patients.length}</div>
          <div className="stat-label">Active Patients</div>
        </div>
        <div className={`stat-card ${unreadAlerts > 0 ? 'stat-warning stat-pulse' : ''}`}>
          <div className="stat-number">{unreadAlerts}</div>
          <div className="stat-label">Unread Alerts</div>
        </div>
        <div className="stat-card stat-info">
          <div className="stat-number">{patients.filter(p => p.ward_name === 'ICU').length}</div>
          <div className="stat-label">In ICU</div>
        </div>
        {user.role === 'admin' && simulatorStatus && (
          <div className="stat-card">
            <div className={`stat-number ${simulatorStatus.running ? 'text-green' : 'text-muted'}`}>
              {simulatorStatus.running ? '●' : '○'}
            </div>
            <div className="stat-label">Simulator {simulatorStatus.running ? 'Running' : 'Stopped'}</div>
          </div>
        )}
      </div>

      {/* Unread Alerts */}
      {unreadAlerts > 0 && (
        <div className="dashboard-alerts">
          <div className="section-header">
            <h2>🔔 Active Alerts</h2>
            <Link to="/alerts" className="btn btn-sm btn-link">View All</Link>
          </div>
          <div className="alerts-list-compact">
            {recentAlerts.map(alert => (
              <div key={alert.alert_id} className={`alert-mini level-${alert.alert_level}`}>
                <span className="alert-mini-icon">
                  {alert.alert_level === 'critical' ? '🔴' : '🟠'}
                </span>
                <span className="alert-mini-patient">{alert.patient_name}</span>
                <span className="alert-mini-time">
                  {alert.created_at ? new Date(alert.created_at).toLocaleTimeString() : ''}
                </span>
                <Link to={`/patients/${alert.patient_id}`} className="btn btn-sm btn-link">View</Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Admin-specific actions */}
      {user.role === 'admin' && (
        <div className="quick-actions">
          <h2>Admin Actions</h2>
          <div className="action-buttons">
            <Link to="/admin/users" className="btn btn-secondary">👥 Manage Users</Link>
            <Link to="/admin/settings" className="btn btn-secondary">⚙️ Settings</Link>
            <Link to="/patients/add" className="btn btn-secondary">➕ Add Patient</Link>
            <Link to="/alerts" className="btn btn-secondary">🔔 Alerts</Link>
            <Link to="/history" className="btn btn-secondary">📋 History</Link>
            {simulatorStatus && (
              <button
                className={`btn ${simulatorStatus.running ? 'btn-danger' : 'btn-primary'}`}
                onClick={toggleSimulator}
              >
                {simulatorStatus.running ? '⏹ Stop Sim' : '▶ Start Sim'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Nurse-specific actions */}
      {user.role === 'nurse' && (
        <div className="quick-actions">
          <h2>Quick Actions</h2>
          <div className="action-buttons">
            <Link to="/patients/add" className="btn btn-secondary">➕ Add Patient</Link>
            <Link to="/vitals/add" className="btn btn-secondary">💉 Record Vitals</Link>
            <Link to="/alerts" className="btn btn-secondary">🔔 View Alerts</Link>
          </div>
        </div>
      )}

      {/* Doctor-specific actions */}
      {user.role === 'doctor' && (
        <div className="quick-actions">
          <h2>Quick Actions</h2>
          <div className="action-buttons">
            <Link to="/alerts" className="btn btn-secondary">🔔 Manage Alerts</Link>
            <Link to="/history" className="btn btn-secondary">📋 Patient History</Link>
          </div>
        </div>
      )}

      {/* Patients Table */}
      <div className="patients-section">
        <div className="section-header">
          <h2>Active Patients</h2>
          <Link to="/patients" className="btn btn-sm">View All</Link>
        </div>

        {patients.length === 0 ? (
          <p className="empty-state">No active patients found.</p>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Bed</th>
                  <th>Ward</th>
                  <th>Doctor</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {patients.slice(0, 10).map((patient) => (
                  <tr key={patient.patient_id}>
                    <td className="patient-name">{patient.full_name}</td>
                    <td>{patient.bed_number || '—'}</td>
                    <td>{patient.ward_name || '—'}</td>
                    <td>{patient.doctor_name || '—'}</td>
                    <td>
                      <span className={`status-badge status-${patient.status}`}>
                        {patient.status}
                      </span>
                    </td>
                    <td>
                      <Link to={`/patients/${patient.patient_id}`} className="btn btn-sm btn-link">
                        View
                      </Link>
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
}
