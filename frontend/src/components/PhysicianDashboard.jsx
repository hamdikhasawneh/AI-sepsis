import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, Heart, Droplets, Wind, Thermometer, Activity, FlaskConical,
  TrendingUp, Brain, AlertTriangle, Users,
} from 'lucide-react';
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import {
  patients, currentVitals, vitalRanges, labResults, initialAlerts,
  getVitalTrends, getRiskTrajectory, getShapValues, getNlpSummary, getModelConfidence,
} from '../mockData';
import AcknowledgeModal from './AcknowledgeModal';
import NotesPanel from './NotesPanel';

/* ── Tooltip ── */
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <p className="label">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="value" style={{ color: p.color }}>{p.name}: {p.value}</p>
      ))}
    </div>
  );
}

/* ── Helpers ── */
function isAbnormal(key, val) {
  const r = vitalRanges[key];
  if (!r) return false;
  return val < r.min || val > r.max;
}

function riskColorHex(level) {
  if (level === 'critical') return '#ff0844';
  if (level === 'high') return '#f97316';
  return '#00f2fe';
}

/* ═══════════════ PHYSICIAN DASHBOARD ═══════════════ */
export default function PhysicianDashboard({ notes = [], onAddNote }) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [selectedId, setSelectedId] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [alerts, setAlerts] = useState(initialAlerts);
  const [modalAlert, setModalAlert] = useState(null);

  /* Filtered patients */
  const filtered = useMemo(() => {
    let list = patients;
    if (filter === 'critical') list = list.filter(p => p.riskLevel === 'critical');
    else if (filter === 'high') list = list.filter(p => p.riskLevel === 'high');
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(p => p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q));
    }
    return list;
  }, [search, filter]);

  const selected = patients.find(p => p.id === selectedId) || null;
  const vitals = selected ? currentVitals[selected.id] : null;
  const trends = useMemo(() => selected ? getVitalTrends(selected.id) : null, [selected]);
  const trajectory = useMemo(() => selected ? getRiskTrajectory(selected.id) : [], [selected]);
  const labs = selected ? (labResults[selected.id] || []) : [];
  const shap = selected ? getShapValues(selected.id) : [];
  const nlp = selected ? getNlpSummary(selected.id) : '';
  const confidence = selected ? getModelConfidence(selected.id) : null;
  const patientAlerts = selected ? alerts.filter(a => a.patientId === selected.id) : [];

  const handleConfirmAlert = (alertId) => {
    setAlerts(prev => prev.filter(a => a.id !== alertId));
    setModalAlert(null);
  };

  const mainTabs = [
    { key: 'overview', label: 'Overview' },
    { key: 'trends', label: 'Vital Trends' },
    { key: 'labs', label: 'Lab Results' },
    { key: 'ai', label: 'AI Reasoning' },
    { key: 'notes', label: 'Notes' },
    { key: 'alerts', label: 'Alerts' },
  ];

  const vitalKPIs = vitals ? [
    { key: 'hr', icon: Heart, label: 'Heart Rate', value: vitals.hr, unit: 'bpm' },
    { key: 'bpSys', icon: Droplets, label: 'Blood Pressure', value: `${vitals.bpSys}/${vitals.bpDia}`, unit: 'mmHg', checkKey: 'bpSys' },
    { key: 'spo2', icon: Activity, label: 'SpO2', value: vitals.spo2, unit: '%' },
    { key: 'rr', icon: Wind, label: 'Resp. Rate', value: vitals.rr, unit: '/min' },
    { key: 'temp', icon: Thermometer, label: 'Temperature', value: vitals.temp, unit: '°C' },
    { key: 'lactate', icon: FlaskConical, label: 'Lactate', value: vitals.lactate, unit: 'mmol/L' },
  ] : [];

  return (
    <div className="physician-layout">
      {/* ── Sidebar ── */}
      <aside className="physician-sidebar">
        <div className="sidebar-search">
          <div className="sidebar-search-wrap">
            <Search size={16} className="sidebar-search-icon" />
            <input
              type="text"
              placeholder="Search patients..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="sidebar-filters">
          {[
            { key: 'all', label: 'All' },
            { key: 'critical', label: 'Critical' },
            { key: 'high', label: 'High Risk' },
          ].map(f => (
            <button
              key={f.key}
              className={`filter-pill ${filter === f.key ? 'active' : ''} ${
                filter === f.key && f.key === 'critical' ? 'critical-filter' : ''
              } ${filter === f.key && f.key === 'high' ? 'high-filter' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="sidebar-patients">
          {filtered.map(p => (
            <div
              key={p.id}
              className={`sidebar-patient-item ${selectedId === p.id ? 'active' : ''}`}
              onClick={() => { setSelectedId(p.id); setActiveTab('overview'); }}
            >
              <div className="sidebar-patient-info">
                <span className="sidebar-patient-name">{p.name}</span>
                <span className="sidebar-patient-meta">{p.id} · {p.bed}</span>
              </div>
              <span className={`sidebar-score-pill ${p.riskLevel}`}>
                {p.sepsisScore}%
              </span>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="empty-state" style={{ padding: 32 }}>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>No patients match</p>
            </div>
          )}
        </div>
      </aside>

      {/* ── Main Content ── */}
      <main className="physician-main">
        {!selected ? (
          <div className="physician-empty">
            <div>
              <Users size={56} className="physician-empty-icon" />
              <p>Select a patient from the sidebar to begin review</p>
            </div>
          </div>
        ) : (
          <motion.div
            key={selected.id}
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            {/* Patient Header */}
            <div className="patient-header">
              <div className="patient-header-left">
                <h1>{selected.name}</h1>
                <p className="patient-header-demographics">
                  {selected.age} y/o · {selected.gender} · {selected.bed} · Admitted {selected.admitDate}
                </p>
              </div>
              <div className={`patient-score-block ${selected.riskLevel}`}>
                <div className="patient-score-number">{selected.sepsisScore}%</div>
                <div className="patient-score-label">{selected.riskLevel} Risk</div>
              </div>
            </div>

            {/* Tabs */}
            <div className="tab-bar">
              {mainTabs.map(t => (
                <button
                  key={t.key}
                  className={`tab-btn ${activeTab === t.key ? 'active' : ''}`}
                  onClick={() => setActiveTab(t.key)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <AnimatePresence mode="wait">
              {/* ── Overview ── */}
              {activeTab === 'overview' && (
                <motion.div key="overview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="vital-kpi-grid">
                    {vitalKPIs.map(v => {
                      const abnKey = v.checkKey || v.key;
                      const abnormal = typeof v.value === 'number' ? isAbnormal(abnKey, v.value) : isAbnormal('bpSys', vitals.bpSys);
                      const Icon = v.icon;
                      return (
                        <div key={v.key} className={`glass-card vital-kpi-card ${abnormal ? 'abnormal' : ''}`}>
                          <Icon size={22} className="vital-kpi-icon" />
                          <div className="vital-kpi-value">{v.value}</div>
                          <div className="vital-kpi-label">{v.label}</div>
                          <div className="vital-kpi-unit">{v.unit}</div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="glass-card chart-wrapper">
                    <h3>
                      <TrendingUp size={18} style={{ color: riskColorHex(selected.riskLevel) }} />
                      24-Hour Risk Trajectory
                    </h3>
                    <ResponsiveContainer width="100%" height={280}>
                      <AreaChart data={trajectory}>
                        <defs>
                          <linearGradient id="trajGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={riskColorHex(selected.riskLevel)} stopOpacity={0.3} />
                            <stop offset="100%" stopColor={riskColorHex(selected.riskLevel)} stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                        <XAxis dataKey="time" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                        <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                        <Tooltip content={<CustomTooltip />} />
                        <ReferenceLine y={70} stroke="#ff0844" strokeDasharray="6 4" strokeWidth={1.5} label={{ value: 'Critical 70%', fill: '#ff0844', fontSize: 11, position: 'right' }} />
                        <Area type="monotone" dataKey="value" name="Risk %" stroke={riskColorHex(selected.riskLevel)} fill="url(#trajGrad)" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </motion.div>
              )}

              {/* ── Vital Trends ── */}
              {activeTab === 'trends' && trends && (
                <motion.div key="trends" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="chart-grid-2x2">
                    {/* HR */}
                    <div className="glass-card chart-wrapper">
                      <h3><Heart size={16} style={{ color: '#4f8ef7' }} /> Heart Rate</h3>
                      <ResponsiveContainer width="100%" height={200}>
                        <AreaChart data={trends.hr}>
                          <defs>
                            <linearGradient id="hrGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#4f8ef7" stopOpacity={0.25} />
                              <stop offset="100%" stopColor="#4f8ef7" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                          <XAxis dataKey="time" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip content={<CustomTooltip />} />
                          <Area type="monotone" dataKey="value" name="HR" stroke="#4f8ef7" fill="url(#hrGrad)" strokeWidth={2} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>

                    {/* BP Multi-line */}
                    <div className="glass-card chart-wrapper">
                      <h3><Droplets size={16} style={{ color: '#34d399' }} /> Blood Pressure</h3>
                      <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={trends.bpSys.map((d, i) => ({
                          time: d.time,
                          systolic: d.value,
                          diastolic: trends.bpDia[i]?.value || 60,
                        }))}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                          <XAxis dataKey="time" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip content={<CustomTooltip />} />
                          <Line type="monotone" dataKey="systolic" name="Systolic" stroke="#34d399" strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="diastolic" name="Diastolic" stroke="#6ee7b7" strokeWidth={2} dot={false} strokeDasharray="4 2" />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>

                    {/* RR */}
                    <div className="glass-card chart-wrapper">
                      <h3><Wind size={16} style={{ color: '#a78bfa' }} /> Respiratory Rate</h3>
                      <ResponsiveContainer width="100%" height={200}>
                        <AreaChart data={trends.rr}>
                          <defs>
                            <linearGradient id="rrGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#a78bfa" stopOpacity={0.25} />
                              <stop offset="100%" stopColor="#a78bfa" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                          <XAxis dataKey="time" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip content={<CustomTooltip />} />
                          <Area type="monotone" dataKey="value" name="RR" stroke="#a78bfa" fill="url(#rrGrad)" strokeWidth={2} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Temp */}
                    <div className="glass-card chart-wrapper">
                      <h3><Thermometer size={16} style={{ color: '#f97316' }} /> Temperature</h3>
                      <ResponsiveContainer width="100%" height={200}>
                        <AreaChart data={trends.temp}>
                          <defs>
                            <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#f97316" stopOpacity={0.25} />
                              <stop offset="100%" stopColor="#f97316" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                          <XAxis dataKey="time" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                          <YAxis domain={[35.5, 40.5]} tick={{ fontSize: 10 }} />
                          <Tooltip content={<CustomTooltip />} />
                          <Area type="monotone" dataKey="value" name="Temp °C" stroke="#f97316" fill="url(#tempGrad)" strokeWidth={2} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* ── Lab Results ── */}
              {activeTab === 'labs' && (
                <motion.div key="labs" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
                    <div className="lab-table-wrap">
                      <table className="lab-table">
                        <thead>
                          <tr>
                            <th>Test</th>
                            <th>Result</th>
                            <th>Reference Range</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {labs.map((lab, i) => (
                            <tr key={i}>
                              <td style={{ fontWeight: 500 }}>{lab.test}</td>
                              <td>{lab.value} {lab.unit}</td>
                              <td style={{ color: 'var(--text-muted)' }}>{lab.range}</td>
                              <td>
                                <span className={`lab-status-badge ${lab.status}`}>
                                  {lab.status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* ── AI Reasoning ── */}
              {activeTab === 'ai' && confidence && (
                <motion.div key="ai" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="ai-reasoning">
                    {/* Model Confidence KPIs */}
                    <div className="ai-confidence-kpis">
                      {[
                        { label: 'Model Confidence', value: `${confidence.confidence}%` },
                        { label: 'Sensitivity', value: `${confidence.sensitivity}%` },
                        { label: 'Specificity', value: `${confidence.specificity}%` },
                        { label: 'AUC Score', value: confidence.auc.toFixed(3) },
                      ].map((kpi, i) => (
                        <div key={i} className="glass-card ai-confidence-card">
                          <div className="ai-confidence-value">{kpi.value}</div>
                          <div className="ai-confidence-label">{kpi.label}</div>
                        </div>
                      ))}
                    </div>

                    {/* NLP Summary */}
                    <div className="nlp-summary-box">
                      <h4>
                        <Brain size={16} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                        AI Clinical Summary
                      </h4>
                      <p className="nlp-summary-text">{nlp}</p>
                    </div>

                    {/* SHAP Chart */}
                    <div className="glass-card shap-chart">
                      <h4>SHAP Feature Impact Analysis</h4>
                      <div className="shap-divider-labels">
                        <span>← Decreases Risk</span>
                        <span>Increases Risk →</span>
                      </div>
                      {shap.map((item, i) => {
                        const barWidth = Math.abs(item.impact) * 45;
                        return (
                          <div key={i} className="shap-row">
                            <div className="shap-feature-label">{item.feature}</div>
                            <div className="shap-bar-container">
                              <div className="shap-center-line" />
                              <div
                                className={`shap-bar ${item.direction}`}
                                style={{ width: `${barWidth}%` }}
                              />
                            </div>
                            <div className="shap-impact-value">
                              {item.direction === 'increase' ? '+' : '−'}{(item.impact * 100).toFixed(0)}%
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </motion.div>
              )}

              {/* ── Alerts ── */}
              {activeTab === 'alerts' && (
                <motion.div key="alerts" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  {patientAlerts.length === 0 ? (
                    <div className="glass-card empty-state">
                      <p style={{ color: 'var(--text-muted)' }}>No active alerts for this patient</p>
                    </div>
                  ) : (
                    <div className="alerts-feed">
                      {patientAlerts.map(alert => (
                        <motion.div
                          key={alert.id}
                          className={`glass-card alert-item ${alert.level}`}
                          layout
                        >
                          <div className={`alert-dot ${alert.level}`} />
                          <div className="alert-content">
                            <h4>{alert.title}</h4>
                            <p>{alert.message}</p>
                            <div className="alert-meta">
                              <span>{new Date(alert.timestamp).toLocaleString()}</span>
                            </div>
                          </div>
                          <div className="alert-actions">
                            <button className="btn-acknowledge" onClick={() => setModalAlert(alert)}>
                              Acknowledge
                            </button>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  )}
                </motion.div>
              )}
              {/* ── Notes ── */}
              {activeTab === 'notes' && selected && (
                <motion.div key="notes" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <NotesPanel
                    patientId={selected.id}
                    patientName={selected.name}
                    notes={notes}
                    onAddNote={onAddNote}
                    currentRole="physician"
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </main>

      {/* Acknowledge Modal */}
      {modalAlert && (
        <AcknowledgeModal
          alert={modalAlert}
          onClose={() => setModalAlert(null)}
          onConfirm={handleConfirmAlert}
        />
      )}
    </div>
  );
}
