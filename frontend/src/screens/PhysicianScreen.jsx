import { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, Heart, Droplets, Wind, Thermometer, Activity,
  TrendingUp, Brain, Users, Plus, Clock, Clipboard, CheckCircle2, AlertTriangle,
} from 'lucide-react';
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { useAppStore, authFetch } from '../store/appStore';
import { Card, CardBody } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge, RiskBadge } from '../components/ui/Badge';
import { Input, Select, Textarea } from '../components/ui/Input';
import { TabList } from '../components/ui/Tabs';
import { Modal } from '../components/ui/Modal';
import { VitalCard, isAbnormal } from '../components/shared/VitalCard';
import { ChartTooltip } from '../components/shared/ChartTooltip';
import { SimulationControl } from '../components/SimulationControl';

const API_BASE = 'http://localhost:8000/api';

const TABS = [
  { key: 'overview', label: 'Overview'     },
  { key: 'trends',   label: 'Vital Trends' },
  { key: 'labs',     label: 'Lab Results'  },
  { key: 'ai',       label: 'AI Reasoning' },
  { key: 'tasks',    label: 'Tasks'        },
  { key: 'alerts',   label: 'Alerts'       },
];

function riskHex(level) {
  if (level === 'critical') return '#F43F5E';
  if (level === 'high') return '#F97316';
  return '#10B981';
}

function genSummary(pred, shap) {
  if (!pred) return 'No prediction data available for this patient.';
  const pct = Math.round(pred.risk_score * 100);
  
  if (!shap || shap.length === 0) {
    return `The Dynamic Survival Transformer v2 model has analyzed the patient's recent physiological trajectories over the last ${pred.input_window_hours} hours. The current prediction indicates a ${pct}% probability of sepsis onset within the next 12-hour risk horizon. Detailed feature attributions are currently unavailable for this prediction window.`;
  }

  const topRisk = shap.filter(f => f.direction === 'increase').slice(0, 3).map(f => f.feature).join(', ');
  const topProtective = shap.filter(f => f.direction === 'decrease').slice(0, 2).map(f => f.feature).join(', ');
  
  const tier = pred.risk_level === 'critical' ? 'critical' : pred.risk_level === 'high_risk' ? 'elevated' : 'low';
  
  let summary = `The Dynamic Survival Transformer v2 model has analyzed the patient's recent physiological trajectories over the last ${pred.input_window_hours} hours. The current prediction indicates a ${pct}% probability of sepsis onset within the next 12-hour risk horizon, placing the patient in the ${tier} risk tier.\n\n`;
  
  if (topRisk) {
    summary += `Key contributing factors driving this risk assessment include elevated deviations in ${topRisk}, which strongly increased the model's risk score. `;
  }
  
  if (topProtective) {
    summary += `Conversely, trends in ${topProtective} currently exhibit a protective effect, slightly decreasing the overall predicted severity. `;
  }
  
  summary += `Clinical teams should carefully monitor these specific physiological indicators and consider early intervention protocols if the risk trajectory continues to climb.`;
  
  return summary;
}

export default function PhysicianScreen() {
  const patients = useAppStore(s => s.patients);
  const tasks    = useAppStore(s => s.tasks);
  const labs     = useAppStore(s => s.labs);
  const alerts   = useAppStore(s => s.alerts);
  const addTask        = useAppStore(s => s.addTask);
  const acknowledgeAlert = useAppStore(s => s.acknowledgeAlert);

  const [search, setSearch]     = useState('');
  const [filter, setFilter]     = useState('all');
  const [selectedId, setSelectedId] = useState(null);
  const [activeTab, setActiveTab]   = useState('overview');
  const [ackAlert, setAckAlert]     = useState(null);
  const [ackNote, setAckNote]       = useState('');
  const [notes, setNotes]           = useState([]);
  const [newNote, setNewNote]       = useState('');

  const [taskText, setTaskText]         = useState('');
  const [taskTime, setTaskTime]         = useState('');
  const [taskType, setTaskType]         = useState('medication');
  const [taskPriority, setTaskPriority] = useState('medium');

  // Per-patient data
  const [vitals, setVitals]           = useState(null);
  const [vitalHistory, setVitalHistory] = useState([]);
  const [trajectory, setTrajectory]   = useState([]);
  const [shapData, setShapData]       = useState([]);
  const [prediction, setPrediction]   = useState(null);

  useEffect(() => {
    if (!selectedId) return;
    setVitals(null); setVitalHistory([]); setTrajectory([]); setShapData([]); setPrediction(null);

    authFetch(`${API_BASE}/vitals/${selectedId}`)
      .then(r => r.json()).then(data => {
        if (data.length) {
          const l = data[data.length - 1];
          setVitals({ hr: l.heart_rate, rr: l.respiratory_rate, temp: l.temperature, spo2: l.spo2, bpSys: l.systolic_bp, bpDia: l.diastolic_bp });
          setVitalHistory(data);
        }
      }).catch(() => {});

    authFetch(`${API_BASE}/predictions/${selectedId}?limit=24`)
      .then(r => r.json()).then(data => {
        setTrajectory([...data].reverse().map(p => ({
          time: new Date(p.predicted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          value: Math.round(p.risk_score * 100),
        })));
        if (data.length) setPrediction(data[0]);
      }).catch(() => {});

    authFetch(`${API_BASE}/predictions/${selectedId}/shap`)
      .then(r => r.ok ? r.json() : null).then(data => {
        if (data?.features) setShapData(data.features.map(f => ({
          feature: f.feature,
          impact: Math.abs(f.shap_value),
          direction: f.direction === 'Risk +' ? 'increase' : 'decrease',
        })));
      }).catch(() => {});
  }, [selectedId]);

  const filtered = useMemo(() => {
    let list = filter === 'critical' ? patients.filter(p => p.riskLevel === 'critical')
             : filter === 'high'     ? patients.filter(p => p.riskLevel === 'high')
             : patients;
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(p => p.name.toLowerCase().includes(q) || String(p.id).includes(q) || p.bed?.toLowerCase().includes(q));
    }
    return list;
  }, [patients, search, filter]);

  const selected = patients.find(p => p.id === selectedId) || null;
  const patientLabs   = selected ? (labs[selected.id] || []) : [];
  const patientAlerts = selected ? alerts.filter(a => a.patientId === selected.id) : [];
  const patientTasks  = selected ? tasks.filter(t => t.patientId === selected.id) : [];

  const trends = useMemo(() => {
    if (!vitalHistory.length) return null;
    const m = key => vitalHistory.map(v => ({
      time: new Date(v.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      value: v[key],
    }));
    return { hr: m('heart_rate'), bpSys: m('systolic_bp'), bpDia: m('diastolic_bp'), rr: m('respiratory_rate'), temp: m('temperature') };
  }, [vitalHistory]);

  const handleConfirmAck = async () => {
    if (!ackNote.trim() || !ackAlert) return;
    await acknowledgeAlert(ackAlert.id);
    setAckAlert(null); setAckNote('');
  };

  const riskColor = riskHex(selected?.riskLevel);

  return (
    <div className="flex h-[calc(100vh-56px)] overflow-hidden bg-void-950">
      {/* Sidebar */}
      <aside className="w-72 flex-shrink-0 border-r border-slate-800 flex flex-col bg-void-950">
        {/* Search + Filter */}
        <div className="p-3 border-b border-slate-800 space-y-2">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-brand-500 transition-colors"
              placeholder="Search patients..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="flex gap-1">
            {[['all','All'],['critical','Critical'],['high','High']].map(([k,l]) => (
              <button key={k} onClick={() => setFilter(k)}
                className={`flex-1 py-1.5 px-2 rounded-md text-xs font-medium transition-all
                  ${filter === k
                    ? k === 'critical' ? 'bg-rose-500/15 text-rose-400 border border-rose-500/25'
                    : k === 'high'     ? 'bg-orange-500/15 text-orange-400 border border-orange-500/25'
                    : 'bg-slate-800 text-slate-200 border border-slate-700'
                    : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50'}`}>
                {l}
              </button>
            ))}
          </div>
        </div>

        {/* Patient list */}
        <div className="flex-1 overflow-y-auto py-1">
          {filtered.map(p => (
            <button
              key={p.id}
              onClick={() => { setSelectedId(p.id); setActiveTab('overview'); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-all group
                ${selectedId === p.id ? 'bg-slate-800' : 'hover:bg-slate-900'}`}
            >
              <div className={`w-1.5 h-6 rounded-full flex-shrink-0 ${p.riskLevel === 'critical' ? 'bg-rose-500' : p.riskLevel === 'high' ? 'bg-orange-500' : 'bg-emerald-500'}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <p className="text-sm font-medium text-slate-200 truncate">{p.name}</p>
                  {p.ward === 'Simulation Lab' && (
                    <span className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[9px] px-1.5 py-0.5 rounded uppercase font-bold tracking-tighter">SIM</span>
                  )}
                </div>
                <p className="text-xs text-slate-500">
                  {p.ward === 'Simulation Lab' && p.simulationHour !== null 
                    ? `Hour ${p.simulationHour} · ${p.bed}` 
                    : p.bed}
                </p>
              </div>
              <RiskBadge level={p.riskLevel} score={p.sepsisScore} />
            </button>
          ))}
          {filtered.length === 0 && (
            <p className="text-center text-xs text-slate-600 py-8">No patients match</p>
          )}
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        {!selected ? (
          <div className="h-full flex flex-col items-center justify-center gap-3 text-center">
            <Users size={40} className="text-slate-700" />
            <p className="text-sm text-slate-500">Select a patient to begin review</p>
          </div>
        ) : (
          <motion.div key={selected.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }}>
            {/* Patient header */}
            <div className="sticky top-0 z-20 bg-void-950/95 backdrop-blur-sm border-b border-slate-800 px-6 py-4 flex items-center justify-between">
              <div>
                <h1 className="text-lg font-bold text-slate-100">{selected.name}</h1>
                <p className="text-xs text-slate-500 mt-0.5">{selected.age} y/o · {selected.gender} · {selected.bed} · Admitted {selected.admitDate}</p>
              </div>
              <div className="flex items-center gap-4">
                {patientAlerts.length > 0 && (
                  <Button onClick={() => setAckAlert(patientAlerts[0])} className="bg-rose-600 hover:bg-rose-500 border-none shadow-[0_0_15px_rgba(225,29,72,0.4)] transition-all flex items-center">
                    <AlertTriangle size={16} className="mr-1.5" /> Acknowledge Alert
                  </Button>
                )}
                <div className={`text-right px-4 py-2.5 rounded-xl border
                  ${selected.riskLevel === 'critical' ? 'bg-rose-500/8 border-rose-500/20' : selected.riskLevel === 'high' ? 'bg-orange-500/8 border-orange-500/20' : 'bg-emerald-500/8 border-emerald-500/20'}`}>
                  <div className={`text-3xl font-mono font-bold ${selected.riskLevel === 'critical' ? 'text-rose-400' : selected.riskLevel === 'high' ? 'text-orange-400' : 'text-emerald-400'}`}>
                    {selected.sepsisScore}%
                  </div>
                  <div className="text-xs text-slate-500 capitalize">{selected.riskLevel} risk</div>
                </div>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Tabs */}
              <TabList tabs={TABS} active={activeTab} onChange={setActiveTab} />

              <AnimatePresence mode="wait">
                {/* Overview */}
                {activeTab === 'overview' && (
                  <motion.div key="ov" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                    {vitals ? (
                      <div className="grid grid-cols-5 gap-3 mb-6">
                        {[
                          { icon: Heart,       label: 'Heart Rate',  value: vitals.hr,   unit: 'bpm',  key: 'hr'    },
                          { icon: Droplets,    label: 'Systolic BP', value: vitals.bpSys, unit: 'mmHg', key: 'bpSys' },
                          { icon: Activity,    label: 'SpO2',        value: vitals.spo2, unit: '%',    key: 'spo2'  },
                          { icon: Wind,        label: 'Resp. Rate',  value: vitals.rr,   unit: '/min', key: 'rr'    },
                          { icon: Thermometer, label: 'Temperature', value: vitals.temp, unit: '°C',   key: 'temp'  },
                        ].map(v => <VitalCard key={v.key} {...v} />)}
                      </div>
                    ) : (
                      <Card className="mb-6">
                        <CardBody className="text-sm text-slate-500">No vital signs recorded yet.</CardBody>
                      </Card>
                    )}

                    <Card>
                      <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-2">
                        <TrendingUp size={15} style={{ color: riskColor }} />
                        <h3 className="text-sm font-semibold text-slate-200">Risk Trajectory</h3>
                        <span className="text-xs text-slate-500 ml-auto">Last 24 predictions</span>
                      </div>
                      <CardBody>
                        {trajectory.length > 0 ? (
                          <ResponsiveContainer width="100%" height={260}>
                            <AreaChart data={trajectory}>
                              <defs>
                                <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="0%" stopColor={riskColor} stopOpacity={0.25} />
                                  <stop offset="100%" stopColor={riskColor} stopOpacity={0} />
                                </linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                              <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#475569' }} interval="preserveStartEnd" />
                              <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#475569' }} />
                              <Tooltip content={<ChartTooltip />} />
                              <ReferenceLine y={70} stroke="#F43F5E" strokeDasharray="6 3" strokeOpacity={0.5}
                                label={{ value: 'Critical 70%', fill: '#F43F5E', fontSize: 10, position: 'right' }} />
                              <Area type="monotone" dataKey="value" name="Risk %" stroke={riskColor} fill="url(#riskGrad)" strokeWidth={2} dot={false} />
                            </AreaChart>
                          </ResponsiveContainer>
                        ) : (
                          <p className="text-sm text-slate-500 py-4">No prediction history yet.</p>
                        )}
                      </CardBody>
                    </Card>
                  </motion.div>
                )}

                {/* Vital Trends */}
                {activeTab === 'trends' && (
                  <motion.div key="tr" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                    {trends ? (
                      <div className="grid grid-cols-2 gap-4">
                        {[
                          { title: 'Heart Rate', color: '#4B7CF7', key: 'hr', name: 'HR (bpm)', icon: Heart },
                          { title: 'Blood Pressure', color: '#10B981', key: 'bp', name: 'Systolic', icon: Droplets },
                          { title: 'Respiratory Rate', color: '#A78BFA', key: 'rr', name: 'RR (/min)', icon: Wind },
                          { title: 'Temperature', color: '#F97316', key: 'temp', name: 'Temp (°C)', icon: Thermometer },
                        ].map(c => {
                          const Icon = c.icon;
                          const data = c.key === 'bp'
                            ? trends.bpSys.map((d, i) => ({ time: d.time, systolic: d.value, diastolic: trends.bpDia[i]?.value ?? null }))
                            : trends[c.key];
                          return (
                            <Card key={c.key}>
                              <div className="px-5 py-3.5 border-b border-slate-800 flex items-center gap-2">
                                <Icon size={14} style={{ color: c.color }} />
                                <span className="text-sm font-medium text-slate-200">{c.title}</span>
                              </div>
                              <CardBody className="pt-4">
                                <ResponsiveContainer width="100%" height={180}>
                                  {c.key === 'bp' ? (
                                    <LineChart data={data}>
                                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                                      <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#475569' }} interval="preserveStartEnd" />
                                      <YAxis tick={{ fontSize: 10, fill: '#475569' }} />
                                      <Tooltip content={<ChartTooltip />} />
                                      <Line type="monotone" dataKey="systolic" name="Systolic" stroke={c.color} strokeWidth={2} dot={false} />
                                      <Line type="monotone" dataKey="diastolic" name="Diastolic" stroke="#6EE7B7" strokeWidth={2} dot={false} strokeDasharray="4 2" />
                                    </LineChart>
                                  ) : (
                                    <AreaChart data={data}>
                                      <defs>
                                        <linearGradient id={`g-${c.key}`} x1="0" y1="0" x2="0" y2="1">
                                          <stop offset="0%" stopColor={c.color} stopOpacity={0.2} />
                                          <stop offset="100%" stopColor={c.color} stopOpacity={0} />
                                        </linearGradient>
                                      </defs>
                                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                                      <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#475569' }} interval="preserveStartEnd" />
                                      <YAxis tick={{ fontSize: 10, fill: '#475569' }} />
                                      <Tooltip content={<ChartTooltip />} />
                                      <Area type="monotone" dataKey="value" name={c.name} stroke={c.color} fill={`url(#g-${c.key})`} strokeWidth={2} dot={false} />
                                    </AreaChart>
                                  )}
                                </ResponsiveContainer>
                              </CardBody>
                            </Card>
                          );
                        })}
                      </div>
                    ) : (
                      <Card><CardBody className="text-sm text-slate-500">No vital history available.</CardBody></Card>
                    )}
                  </motion.div>
                )}

                {/* Labs */}
                {activeTab === 'labs' && (
                  <motion.div key="lb" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                    <Card>
                      {patientLabs.length > 0 ? (
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-slate-800">
                              {['Test', 'Result', 'Reference Range', 'Status'].map(h => (
                                <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {patientLabs.map((lab, i) => (
                              <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                                <td className="px-5 py-3 font-medium text-slate-200">{lab.test}</td>
                                <td className="px-5 py-3 font-mono text-slate-300">{lab.value} {lab.unit}</td>
                                <td className="px-5 py-3 text-slate-500">{lab.range}</td>
                                <td className="px-5 py-3">
                                  <Badge variant={lab.status === 'critical' ? 'critical' : lab.status === 'high' ? 'high' : 'safe'}>
                                    {lab.status}
                                  </Badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : (
                        <CardBody className="text-sm text-slate-500">No lab results for this patient.</CardBody>
                      )}
                    </Card>
                  </motion.div>
                )}

                {/* AI Reasoning */}
                {activeTab === 'ai' && (
                  <motion.div key="ai" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-4">
                    {prediction && (
                      <div className="grid grid-cols-4 gap-3">
                        {[
                          { label: 'Sepsis Risk',    value: `${Math.round(prediction.risk_score * 100)}%` },
                          { label: 'Risk Level',     value: prediction.risk_level?.replace('_',' ') || '—' },
                          { label: 'Vital Readings', value: prediction.input_window_hours               },
                          { label: 'Model',          value: prediction.model_version || '—'             },
                        ].map((k, i) => (
                          <Card key={i}>
                            <CardBody className="text-center py-4">
                              <div className="text-2xl font-mono font-bold text-slate-100 mb-1">{k.value}</div>
                              <div className="text-xs text-slate-500">{k.label}</div>
                            </CardBody>
                          </Card>
                        ))}
                      </div>
                    )}

                    <Card>
                      <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-2">
                        <Brain size={15} className="text-violet-400" />
                        <h3 className="text-sm font-semibold text-slate-200">AI Clinical Summary</h3>
                      </div>
                      <CardBody>
                        <p className="text-sm text-slate-400 leading-relaxed">{genSummary(prediction, shapData)}</p>
                      </CardBody>
                    </Card>

                    {shapData.length > 0 && (
                      <Card>
                        <div className="px-5 py-4 border-b border-slate-800">
                          <h3 className="text-sm font-semibold text-slate-200">SHAP Feature Attribution</h3>
                          <div className="flex justify-between text-[10px] text-slate-600 mt-1">
                            <span>← Decreases risk</span><span>Increases risk →</span>
                          </div>
                        </div>
                        <CardBody className="space-y-3">
                          {shapData.map((item, i) => {
                            const w = Math.min(Math.abs(item.impact) * 500, 45);
                            return (
                              <div key={i} className="flex items-center gap-3">
                                <span className="text-xs text-slate-400 w-36 flex-shrink-0 truncate">{item.feature}</span>
                                <div className="flex-1 flex items-center justify-center relative h-4">
                                  <div className="absolute inset-x-0 top-1/2 h-px bg-slate-800" />
                                  <div
                                    className={`absolute top-0 h-4 rounded ${item.direction === 'increase' ? 'left-1/2 bg-rose-500/70' : 'right-1/2 bg-emerald-500/70'}`}
                                    style={{ width: `${w}%` }}
                                  />
                                </div>
                                <span className={`text-xs font-mono w-14 text-right ${item.direction === 'increase' ? 'text-rose-400' : 'text-emerald-400'}`}>
                                  {item.direction === 'increase' ? '+' : '−'}{(item.impact * 100).toFixed(1)}%
                                </span>
                              </div>
                            );
                          })}
                        </CardBody>
                      </Card>
                    )}
                  </motion.div>
                )}

                {/* Tasks */}
                {activeTab === 'tasks' && (
                  <motion.div key="tk" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                    <div className="grid grid-cols-[1fr_320px] gap-4">
                      <Card>
                        <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-2">
                          <Clipboard size={15} className="text-slate-500" />
                          <h3 className="text-sm font-semibold text-slate-200">Assigned Tasks</h3>
                        </div>
                        {patientTasks.length === 0 ? (
                          <CardBody className="text-sm text-slate-500">No tasks for this patient.</CardBody>
                        ) : (
                          <div className="divide-y divide-slate-800">
                            {patientTasks.map(t => (
                              <div key={t.id} className={`flex items-center gap-3 px-5 py-3 ${t.done ? 'opacity-50' : ''}`}>
                                {t.done ? <CheckCircle2 size={16} className="text-emerald-500 flex-shrink-0" /> : <Clock size={16} className="text-slate-600 flex-shrink-0" />}
                                <div className="flex-1 min-w-0">
                                  <p className={`text-sm font-medium text-slate-200 ${t.done ? 'line-through' : ''}`}>{t.task}</p>
                                  <p className="text-xs text-slate-500 mt-0.5 capitalize">{t.type} · {t.priority}</p>
                                </div>
                                <span className="text-xs font-mono text-slate-400">{t.time}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </Card>

                      <Card>
                        <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-2">
                          <Plus size={15} className="text-slate-500" />
                          <h3 className="text-sm font-semibold text-slate-200">New Task</h3>
                        </div>
                        <CardBody className="space-y-3">
                          <Input label="Description" type="text" placeholder="e.g. Administer Meropenem 1g" value={taskText} onChange={e => setTaskText(e.target.value)} />
                          <Input label="Scheduled Time" type="time" value={taskTime} onChange={e => setTaskTime(e.target.value)} />
                          <Select label="Type" value={taskType} onChange={e => setTaskType(e.target.value)}>
                            <option value="medication">Medication</option>
                            <option value="lab">Lab Order</option>
                            <option value="vitals">Vitals Check</option>
                            <option value="assessment">Assessment</option>
                          </Select>
                          <Select label="Priority" value={taskPriority} onChange={e => setTaskPriority(e.target.value)}>
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                          </Select>
                          <Button className="w-full justify-center mt-2" disabled={!taskText || !taskTime}
                            onClick={() => {
                              if (!taskText || !taskTime) return;
                              addTask({ patient: selected.name, patientId: selected.id, bed: selected.bed, task: taskText, time: taskTime, type: taskType, priority: taskPriority });
                              setTaskText(''); setTaskTime('');
                            }}>
                            Assign Task
                          </Button>
                        </CardBody>
                      </Card>
                    </div>
                  </motion.div>
                )}

                {/* Alerts */}
                {activeTab === 'alerts' && (
                  <motion.div key="al" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-3">
                    {patientAlerts.length === 0 ? (
                      <Card><CardBody className="text-sm text-slate-500">No active alerts for this patient.</CardBody></Card>
                    ) : patientAlerts.map(alert => (
                      <Card key={alert.id}>
                        <CardBody className="flex items-start gap-4">
                          <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${alert.level === 'critical' ? 'bg-rose-500 shadow-[0_0_6px_rgba(244,63,94,0.8)]' : 'bg-orange-500'}`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant={alert.level === 'critical' ? 'critical' : 'high'}>{alert.title}</Badge>
                            </div>
                            <p className="text-sm text-slate-400">{alert.message}</p>
                            <p className="text-xs text-slate-600 mt-1">{new Date(alert.timestamp).toLocaleString()}</p>
                          </div>
                          <Button size="sm" variant="outline" onClick={() => setAckAlert(alert)}>
                            <AlertTriangle size={13} /> Acknowledge
                          </Button>
                        </CardBody>
                      </Card>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </main>

      {/* Acknowledge Modal */}
      <Modal open={!!ackAlert} onClose={() => { setAckAlert(null); setAckNote(''); }} title="Acknowledge Alert" size="md">
        {ackAlert && (
          <div className="p-6 space-y-4">
            <div className={`p-4 rounded-xl border ${ackAlert.level === 'critical' ? 'bg-rose-500/8 border-rose-500/20' : 'bg-orange-500/8 border-orange-500/20'}`}>
              <Badge variant={ackAlert.level === 'critical' ? 'critical' : 'high'} className="mb-2">{ackAlert.level}</Badge>
              <p className="text-sm text-slate-300">{ackAlert.message}</p>
            </div>
            <Textarea
              label="Clinical Action Note (required)"
              placeholder="Document your clinical response..."
              value={ackNote}
              onChange={e => setAckNote(e.target.value)}
              rows={4}
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => { setAckAlert(null); setAckNote(''); }}>Cancel</Button>
              <Button disabled={!ackNote.trim()} onClick={handleConfirmAck}>Confirm &amp; Dismiss</Button>
            </div>
          </div>
        )}
      </Modal>
      {/* Simulation Lab Control */}
      <SimulationControl />
    </div>
  );
}
