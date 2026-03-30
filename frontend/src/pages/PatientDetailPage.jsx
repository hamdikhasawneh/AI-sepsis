import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';

export default function PatientDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [patient, setPatient] = useState(null);
  const [vitals, setVitals] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPatientData();
  }, [id]);

  const loadPatientData = async () => {
    try {
      const [patientRes, vitalsRes, predsRes, alertsRes] = await Promise.all([
        api.get(`/patients/${id}`),
        api.get(`/vitals/${id}`, { params: { hours: 12 } }),
        api.get(`/predictions/${id}`),
        api.get('/alerts/', { params: { patient_id: id } }),
      ]);
      setPatient(patientRes.data);
      setVitals(vitalsRes.data.reverse());
      setPredictions(predsRes.data);
      setAlerts(alertsRes.data);
    } catch (err) {
      console.error('Failed to load patient:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (alertId) => {
    try {
      await api.patch(`/alerts/${alertId}/read`);
      loadPatientData();
    } catch (err) {
      console.error('Failed to mark alert:', err);
    }
  };

  if (loading) return <div className="loading">Loading patient details...</div>;
  if (!patient) return <div className="error">Patient not found.</div>;

  const chartData = vitals.map(v => ({
    time: new Date(v.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    hr: v.heart_rate,
    rr: v.respiratory_rate,
    temp: v.temperature,
    spo2: v.spo2,
    sbp: v.systolic_bp,
    dbp: v.diastolic_bp,
  }));

  const riskChartData = [...predictions].reverse().map(p => ({
    time: new Date(p.predicted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    risk: Math.round(p.risk_score * 100),
    threshold: Math.round((p.threshold_used || 0.8) * 100),
  }));

  const latestPrediction = predictions[0];
  const unreadAlerts = alerts.filter(a => !a.is_read);

  return (
    <div className="patient-detail-page">
      <div className="page-header">
        <div>
          <Link to="/patients" className="back-link">← Back to Patients</Link>
          <h1>{patient.full_name}</h1>
        </div>
        <div className="header-badges">
          <span className={`status-badge status-${patient.status}`}>{patient.status}</span>
          {latestPrediction && (
            <span className={`risk-badge risk-${latestPrediction.risk_level}`}>
              Risk: {(latestPrediction.risk_score * 100).toFixed(1)}%
              ({latestPrediction.risk_level})
            </span>
          )}
        </div>
      </div>

      {/* Unread Alert Banner */}
      {unreadAlerts.length > 0 && (
        <div className="alert-banner">
          <span>⚠️ {unreadAlerts.length} active alert{unreadAlerts.length > 1 ? 's' : ''} for this patient</span>
          <Link to="#alerts-section" className="btn btn-sm btn-primary">View Alerts</Link>
        </div>
      )}

      {/* Patient Info + Risk */}
      <div className="info-grid">
        <div className="info-card">
          <h3>Patient Information</h3>
          <div className="info-rows">
            <div className="info-row"><span>Age:</span><span>{patient.age || '—'}</span></div>
            <div className="info-row"><span>Gender:</span><span>{patient.gender || '—'}</span></div>
            <div className="info-row"><span>Date of Birth:</span><span>{patient.date_of_birth || '—'}</span></div>
            <div className="info-row"><span>Bed:</span><span>{patient.bed_number || '—'}</span></div>
            <div className="info-row"><span>Ward:</span><span>{patient.ward_name || '—'}</span></div>
            <div className="info-row"><span>Doctor:</span><span>{patient.doctor_name || 'Unassigned'}</span></div>
            <div className="info-row">
              <span>Admitted:</span>
              <span>{patient.admission_time ? new Date(patient.admission_time).toLocaleString() : '—'}</span>
            </div>
          </div>
        </div>

        <div className="info-card">
          <h3>Diagnosis & Notes</h3>
          <p className="notes-text">{patient.diagnosis_notes || 'No notes recorded.'}</p>

          {latestPrediction && (
            <div className="risk-summary">
              <h4>Latest Risk Assessment</h4>
              <div className="risk-gauge">
                <div className="risk-gauge-bar">
                  <div
                    className={`risk-gauge-fill risk-${latestPrediction.risk_level}`}
                    style={{ width: `${latestPrediction.risk_score * 100}%` }}
                  />
                </div>
                <span className="risk-gauge-label">
                  {(latestPrediction.risk_score * 100).toFixed(1)}%
                </span>
              </div>
              <p className="risk-time">
                Model: {latestPrediction.model_version} | Window: {latestPrediction.input_window_hours}h |
                {' '}{new Date(latestPrediction.predicted_at).toLocaleString()}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Risk Score Trend */}
      {riskChartData.length > 0 && (
        <div className="chart-section">
          <h2>Sepsis Risk Trend</h2>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={riskChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="time" stroke="#888" fontSize={12} />
                <YAxis stroke="#888" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  contentStyle={{ background: '#1e1e2f', border: '1px solid #333' }}
                  formatter={(v) => [`${v}%`]}
                />
                <Legend />
                <Area type="monotone" dataKey="risk" stroke="#ff6b6b" fill="rgba(255,107,107,0.15)" name="Risk Score" />
                <Line type="monotone" dataKey="threshold" stroke="#ffd93d" strokeDasharray="5 5" name="Threshold" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Vitals Charts */}
      <div className="chart-section">
        <h2>Vital Signs Over Time</h2>
        {chartData.length === 0 ? (
          <p className="empty-state">No vitals recorded yet.</p>
        ) : (
          <>
            <div className="chart-container">
              <h3>Heart Rate & SpO2</h3>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="time" stroke="#888" fontSize={12} />
                  <YAxis stroke="#888" />
                  <Tooltip contentStyle={{ background: '#1e1e2f', border: '1px solid #333' }} />
                  <Legend />
                  <Line type="monotone" dataKey="hr" stroke="#ff6b6b" name="Heart Rate" dot={false} />
                  <Line type="monotone" dataKey="spo2" stroke="#4ecdc4" name="SpO2" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-container">
              <h3>Blood Pressure</h3>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="time" stroke="#888" fontSize={12} />
                  <YAxis stroke="#888" />
                  <Tooltip contentStyle={{ background: '#1e1e2f', border: '1px solid #333' }} />
                  <Legend />
                  <Line type="monotone" dataKey="sbp" stroke="#ffd93d" name="Systolic BP" dot={false} />
                  <Line type="monotone" dataKey="dbp" stroke="#6bcb77" name="Diastolic BP" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-container">
              <h3>Temperature & Respiratory Rate</h3>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="time" stroke="#888" fontSize={12} />
                  <YAxis stroke="#888" />
                  <Tooltip contentStyle={{ background: '#1e1e2f', border: '1px solid #333' }} />
                  <Legend />
                  <Line type="monotone" dataKey="temp" stroke="#ff9f43" name="Temperature" dot={false} />
                  <Line type="monotone" dataKey="rr" stroke="#a29bfe" name="Resp. Rate" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </div>

      {/* Alert History */}
      <div id="alerts-section" className="alerts-history-section">
        <h2>🔔 Alert History</h2>
        {alerts.length === 0 ? (
          <p className="empty-state">No alerts for this patient.</p>
        ) : (
          <div className="alerts-list">
            {alerts.map(alert => (
              <div key={alert.alert_id} className={`alert-card ${alert.is_read ? 'alert-read' : 'alert-unread'} alert-level-${alert.alert_level}`}>
                <div className="alert-card-header">
                  <div className="alert-card-left">
                    <span className={`alert-level-badge level-${alert.alert_level}`}>
                      {alert.alert_level === 'critical' ? '🔴' : '🟠'} {alert.alert_level}
                    </span>
                  </div>
                  <div className="alert-card-right">
                    <span className="alert-time">
                      {alert.created_at ? new Date(alert.created_at).toLocaleString() : ''}
                    </span>
                    {alert.is_read ? (
                      <span className="alert-read-badge">✓ Read by {alert.read_by_name}</span>
                    ) : (
                      user.role === 'doctor' && (
                        <button className="btn btn-sm btn-primary" onClick={() => handleMarkRead(alert.alert_id)}>
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
      </div>

      {/* Prediction History */}
      <div className="predictions-section">
        <h2>📊 Prediction History</h2>
        {predictions.length === 0 ? (
          <p className="empty-state">No predictions yet.</p>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Risk Score</th>
                  <th>Risk Level</th>
                  <th>Threshold</th>
                  <th>Model</th>
                  <th>Window</th>
                </tr>
              </thead>
              <tbody>
                {predictions.slice(0, 15).map(p => (
                  <tr key={p.prediction_id}>
                    <td>{new Date(p.predicted_at).toLocaleString()}</td>
                    <td>
                      <span className={`risk-score-cell risk-${p.risk_level}`}>
                        {(p.risk_score * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td>
                      <span className={`risk-badge risk-${p.risk_level}`}>
                        {p.risk_level}
                      </span>
                    </td>
                    <td>{p.threshold_used ? (p.threshold_used * 100).toFixed(0) + '%' : '—'}</td>
                    <td>{p.model_version || '—'}</td>
                    <td>{p.input_window_hours || 6}h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Vitals Table */}
      <div className="vitals-table-section">
        <h2>Recent Vital Readings</h2>
        {vitals.length === 0 ? (
          <p className="empty-state">No vitals recorded yet.</p>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>HR</th>
                  <th>RR</th>
                  <th>Temp</th>
                  <th>SpO2</th>
                  <th>SBP</th>
                  <th>DBP</th>
                  <th>MBP</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {vitals.slice(-10).reverse().map((v) => (
                  <tr key={v.vital_id}>
                    <td>{new Date(v.recorded_at).toLocaleTimeString()}</td>
                    <td>{v.heart_rate}</td>
                    <td>{v.respiratory_rate}</td>
                    <td>{v.temperature}</td>
                    <td>{v.spo2}</td>
                    <td>{v.systolic_bp}</td>
                    <td>{v.diastolic_bp}</td>
                    <td>{v.mean_bp}</td>
                    <td>
                      <span className={`source-badge source-${v.source}`}>{v.source}</span>
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
