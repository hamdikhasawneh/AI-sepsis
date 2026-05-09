import { useState, useMemo, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users, AlertTriangle, TrendingUp, FlaskConical,
  HeartPulse, Thermometer, Wind, Upload, FileText,
  Heart, Droplets, Activity as ActIcon, User,
  Clock, Pill, Clipboard, CalendarClock, Syringe, ShieldAlert,
  BedDouble, Eye,
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { useAppStore, authFetch } from '../store/appStore';
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge, RiskBadge } from '../components/ui/Badge';
import { Select } from '../components/ui/Input';
import { TabList } from '../components/ui/Tabs';
import { ChartTooltip } from '../components/shared/ChartTooltip';

const API_BASE = 'http://localhost:8000/api';

const VITAL_RANGES = { hr: { min: 60, max: 100 }, bpSys: { min: 90, max: 140 }, spo2: { min: 95, max: 100 }, rr: { min: 12, max: 20 }, temp: { min: 36.0, max: 37.5 } };

const LAB_FIELDS = [
  { key: 'wbc',        label: 'WBC Count',          unit: 'K/µL',   range: '4.5-11.0' },
  { key: 'lactate',    label: 'Serum Lactate',       unit: 'mmol/L', range: '<2.0'     },
  { key: 'crp',        label: 'C-Reactive Protein',  unit: 'mg/L',   range: '<10'      },
  { key: 'procalc',    label: 'Procalcitonin',       unit: 'ng/mL',  range: '<0.5'     },
  { key: 'creatinine', label: 'Creatinine',          unit: 'mg/dL',  range: '0.6-1.2'  },
  { key: 'glucose',    label: 'Blood Glucose',       unit: 'mg/dL',  range: '70-140'   },
  { key: 'platelets',  label: 'Platelet Count',      unit: 'K/µL',   range: '150-400'  },
  { key: 'bilirubin',  label: 'Total Bilirubin',     unit: 'mg/dL',  range: '0.3-1.2'  },
];

function riskHex(l) { return l === 'critical' ? '#F43F5E' : l === 'high' ? '#F97316' : '#10B981'; }

function taskIcon(type) {
  const map = { medication: Pill, lab: FlaskConical, vitals: HeartPulse, assessment: Clipboard };
  return map[type] || Clock;
}

const TABS = [
  { key: 'monitor', label: 'Unit Monitor' },
  { key: 'tasks',   label: 'Tasks'        },
  { key: 'labs',    label: 'Lab Entry'    },
  { key: 'alerts',  label: 'Alerts'       },
];

export default function NurseScreen() {
  const patients   = useAppStore(s => s.patients);
  const tasks      = useAppStore(s => s.tasks);
  const labs       = useAppStore(s => s.labs);
  const alerts     = useAppStore(s => s.alerts);
  const toggleTask = useAppStore(s => s.toggleTask);
  const addLab     = useAppStore(s => s.addLab);

  const [activeTab, setActiveTab] = useState('monitor');
  const [selected, setSelected]   = useState(null);
  const [labMode, setLabMode]     = useState('manual');
  const [uploadPid, setUploadPid] = useState('');
  const [uploadProgress, setUploadProgress] = useState(null);
  const [extractedCount, setExtractedCount] = useState(0);
  const [labForm, setLabForm]     = useState({});
  const [manualPid, setManualPid] = useState('');
  const fileRef = useRef(null);

  const [selVitals, setSelVitals]   = useState([]);
  const [selTraj, setSelTraj]       = useState([]);

  useEffect(() => {
    if (!selected) return;
    setSelVitals([]); setSelTraj([]);
    authFetch(`${API_BASE}/vitals/${selected.id}`).then(r => r.json()).then(setSelVitals).catch(() => {});
    authFetch(`${API_BASE}/predictions/${selected.id}?limit=24`).then(r => r.json()).then(data => {
      setSelTraj([...data].reverse().map(p => ({
        time: new Date(p.predicted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        value: Math.round(p.risk_score * 100),
      })));
    }).catch(() => {});
  }, [selected]);

  const admitted     = patients.filter(p => p.status === 'admitted');
  const sorted       = useMemo(() => [...admitted].sort((a, b) => (['critical','high','safe'].indexOf(a.riskLevel)) - (['critical','high','safe'].indexOf(b.riskLevel))), [admitted]);
  const critCount    = admitted.filter(p => p.riskLevel === 'critical').length;
  const highCount    = admitted.filter(p => p.riskLevel === 'high').length;
  const safeCount    = admitted.filter(p => p.riskLevel === 'safe').length;
  const completedTasks = tasks.filter(t => t.done).length;

  const tabsWithCount = TABS.map(t => {
    if (t.key === 'tasks') return { ...t, label: `Tasks (${tasks.length - completedTasks} left)` };
    if (t.key === 'alerts') return { ...t, label: `Alerts (${alerts.length})` };
    return t;
  });

  const handleUpload = async e => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadProgress(0);
    const iv = setInterval(() => setUploadProgress(p => p >= 90 ? p : p + Math.random() * 15), 300);
    try {
      const token = localStorage.getItem('sepsis_token');
      const fd = new FormData();
      fd.append('patient_id', uploadPid); fd.append('file', file);
      const res = await fetch(`${API_BASE}/documents/upload`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd });
      if (res.ok) {
        const data = await res.json();
        clearInterval(iv); setUploadProgress(100);
        const extracted = data.extracted_labs || [];
        setExtractedCount(extracted.length);
        extracted.forEach(lab => addLab({ patient_id: Number(uploadPid), test_name: lab.test_name, value: lab.value, unit: lab.unit, reference_range: lab.reference_range, status: lab.status }));
      } else throw new Error();
    } catch { clearInterval(iv); setUploadProgress(0); alert('Upload failed.'); }
    if (fileRef.current) fileRef.current.value = '';
  };

  const handleManualSubmit = () => {
    if (!manualPid) return;
    Object.entries(labForm).forEach(([key, val]) => {
      if (!val) return;
      const field = LAB_FIELDS.find(f => f.key === key);
      const num = parseFloat(val);
      let status = 'normal';
      if (field.range.includes('-')) { const [mn,mx] = field.range.split('-').map(Number); if (num < mn || num > mx) status = 'high'; if (num > mx*1.5 || num < mn*0.5) status = 'critical'; }
      else if (field.range.startsWith('<')) { const mx = parseFloat(field.range.slice(1)); if (num > mx) status = 'high'; if (num > mx*2) status = 'critical'; }
      addLab({ patient_id: Number(manualPid), test_name: field.label, value: num, unit: field.unit, reference_range: field.range, status });
    });
    setLabForm({}); setManualPid(''); alert('Lab results submitted.');
  };

  return (
    <div className="min-h-[calc(100vh-56px)] bg-void-950 p-6 space-y-6">
      {/* KPI strip */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total Patients', value: admitted.length, icon: Users,         color: 'text-brand-400',   ring: 'bg-brand-500/10 border-brand-500/15'   },
          { label: 'Critical',       value: critCount,       icon: AlertTriangle,  color: 'text-rose-400',    ring: 'bg-rose-500/10 border-rose-500/15'     },
          { label: 'High Risk',      value: highCount,       icon: TrendingUp,     color: 'text-orange-400',  ring: 'bg-orange-500/10 border-orange-500/15' },
          { label: 'Stable',         value: safeCount,       icon: Heart,          color: 'text-emerald-400', ring: 'bg-emerald-500/10 border-emerald-500/15'},
        ].map(k => {
          const Icon = k.icon;
          return (
            <Card key={k.label}>
              <CardBody className="flex items-center gap-4 py-4">
                <div className={`w-10 h-10 rounded-xl border flex items-center justify-center flex-shrink-0 ${k.ring}`}>
                  <Icon size={18} className={k.color} />
                </div>
                <div>
                  <div className={`text-3xl font-mono font-bold ${k.color}`}>{k.value}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{k.label}</div>
                </div>
              </CardBody>
            </Card>
          );
        })}
      </div>

      {/* Tabs */}
      <TabList tabs={tabsWithCount} active={activeTab} onChange={setActiveTab} />

      <AnimatePresence mode="wait">
        {/* UNIT MONITOR */}
        {activeTab === 'monitor' && (
          <motion.div key="mon" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div className="grid grid-cols-[1fr_380px] gap-4">
              {/* Patient table */}
              <Card>
                <div className="px-5 py-3 border-b border-slate-800 grid grid-cols-[1fr_60px_80px_50px_52px_52px] gap-3 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                  <span>Patient</span><span>Bed</span><span>Risk</span><span>HR</span><span>SpO2</span><span>Temp</span>
                </div>
                <div className="divide-y divide-slate-800/60">
                  {sorted.map(p => {
                    const v = p.latestVitals;
                    const hrAb   = v ? (v.hr < VITAL_RANGES.hr.min || v.hr > VITAL_RANGES.hr.max) : false;
                    const spo2Ab = v ? (v.spo2 < VITAL_RANGES.spo2.min) : false;
                    const tempAb = v ? (v.temp < VITAL_RANGES.temp.min || v.temp > VITAL_RANGES.temp.max) : false;
                    const isSel  = selected?.id === p.id;
                    return (
                      <motion.div
                        key={p.id}
                        className={`grid grid-cols-[1fr_60px_80px_50px_52px_52px] gap-3 items-center px-5 py-3 cursor-pointer transition-colors
                          ${isSel ? 'bg-slate-800' : 'hover:bg-slate-900'}`}
                        onClick={() => setSelected(isSel ? null : p)}
                        layout
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className={`w-1 h-8 rounded-full flex-shrink-0 ${p.riskLevel === 'critical' ? 'bg-rose-500' : p.riskLevel === 'high' ? 'bg-orange-500' : 'bg-emerald-500'}`} />
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-slate-200 truncate">{p.name}</p>
                            <p className="text-[10px] text-slate-500">#{p.id}</p>
                          </div>
                        </div>
                        <span className="text-xs text-slate-400">{p.bed}</span>
                        <RiskBadge level={p.riskLevel} score={p.sepsisScore} />
                        <span className={`text-xs font-mono ${hrAb ? 'text-rose-400 font-semibold' : 'text-slate-300'}`}>{v?.hr ?? '—'}</span>
                        <span className={`text-xs font-mono ${spo2Ab ? 'text-rose-400 font-semibold' : 'text-slate-300'}`}>{v ? `${v.spo2}%` : '—'}</span>
                        <span className={`text-xs font-mono ${tempAb ? 'text-rose-400 font-semibold' : 'text-slate-300'}`}>{v ? `${v.temp}°` : '—'}</span>
                      </motion.div>
                    );
                  })}
                  {sorted.length === 0 && <div className="px-5 py-8 text-sm text-slate-500">No admitted patients.</div>}
                </div>
              </Card>

              {/* Detail panel */}
              <div className="space-y-4">
                <AnimatePresence mode="wait">
                  {selected ? (
                    <motion.div key={selected.id} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} className="space-y-4">
                      <Card>
                        <CardBody>
                          <div className="flex items-start justify-between mb-4">
                            <div>
                              <h3 className="text-base font-bold text-slate-100">{selected.name}</h3>
                              <p className="text-xs text-slate-500 mt-0.5">{selected.age} y/o · {selected.gender} · {selected.bed}</p>
                              <p className="text-xs text-slate-500 mt-0.5">{selected.diagnosis}</p>
                            </div>
                            <div className={`text-right px-3 py-2 rounded-lg border text-center
                              ${selected.riskLevel === 'critical' ? 'bg-rose-500/8 border-rose-500/20' : selected.riskLevel === 'high' ? 'bg-orange-500/8 border-orange-500/20' : 'bg-emerald-500/8 border-emerald-500/20'}`}>
                              <div className={`text-2xl font-mono font-bold ${selected.riskLevel === 'critical' ? 'text-rose-400' : selected.riskLevel === 'high' ? 'text-orange-400' : 'text-emerald-400'}`}>{selected.sepsisScore}%</div>
                              <div className="text-[10px] text-slate-500 capitalize">{selected.riskLevel}</div>
                            </div>
                          </div>

                          {selected.latestVitals && (
                            <div className="grid grid-cols-5 gap-1.5">
                              {[
                                { l: 'HR',   v: selected.latestVitals.hr,   k: 'hr',   ab: isAb('hr', selected.latestVitals.hr)   },
                                { l: 'BP',   v: `${selected.latestVitals.bpSys}/${selected.latestVitals.bpDia}`, k: 'bpSys', ab: isAb('bpSys', selected.latestVitals.bpSys) },
                                { l: 'SpO2', v: `${selected.latestVitals.spo2}%`, k: 'spo2', ab: isAb('spo2', selected.latestVitals.spo2) },
                                { l: 'RR',   v: selected.latestVitals.rr,   k: 'rr',   ab: isAb('rr', selected.latestVitals.rr)   },
                                { l: 'Temp', v: `${selected.latestVitals.temp}°`, k: 'temp', ab: isAb('temp', selected.latestVitals.temp) },
                              ].map(({ l, v, k, ab }) => (
                                <div key={k} className={`rounded-lg p-2 text-center border ${ab ? 'bg-rose-500/6 border-rose-500/15' : 'bg-slate-800 border-slate-700'}`}>
                                  <p className="text-[9px] text-slate-500 mb-0.5">{l}</p>
                                  <p className={`text-xs font-mono font-semibold ${ab ? 'text-rose-400' : 'text-slate-200'}`}>{v}</p>
                                </div>
                              ))}
                            </div>
                          )}
                        </CardBody>
                      </Card>

                      {/* Abnormal labs */}
                      {labs[selected.id]?.filter(l => l.status !== 'normal').length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-xs uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                              <FlaskConical size={12} /> Abnormal Labs
                            </CardTitle>
                          </CardHeader>
                          <CardBody className="grid grid-cols-2 gap-1.5 pt-3">
                            {labs[selected.id].filter(l => l.status !== 'normal').slice(0,6).map((lab, i) => (
                              <div key={i} className="flex justify-between items-center bg-slate-800 rounded-lg px-2.5 py-1.5">
                                <span className="text-[10px] text-slate-400 truncate">{lab.test}</span>
                                <span className={`text-[10px] font-mono font-bold ml-1 ${lab.status === 'critical' ? 'text-rose-400' : 'text-orange-400'}`}>{lab.value} {lab.unit}</span>
                              </div>
                            ))}
                          </CardBody>
                        </Card>
                      )}

                      {/* Risk Trend */}
                      <Card>
                        <CardHeader>
                          <CardTitle className="flex items-center gap-2">
                            <TrendingUp size={14} style={{ color: riskHex(selected.riskLevel) }} />
                            Risk Trend
                          </CardTitle>
                        </CardHeader>
                        <CardBody className="pt-3">
                          {selTraj.length > 0 ? (
                            <ResponsiveContainer width="100%" height={160}>
                              <AreaChart data={selTraj}>
                                <defs>
                                  <linearGradient id="rg2" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor={riskHex(selected.riskLevel)} stopOpacity={0.25} />
                                    <stop offset="100%" stopColor={riskHex(selected.riskLevel)} stopOpacity={0} />
                                  </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                                <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#475569' }} interval="preserveStartEnd" />
                                <YAxis domain={[0,100]} tick={{ fontSize: 9, fill: '#475569' }} />
                                <Tooltip content={<ChartTooltip />} />
                                <ReferenceLine y={70} stroke="#F43F5E" strokeDasharray="4 3" strokeOpacity={0.5} />
                                <Area type="monotone" dataKey="value" name="Risk %" stroke={riskHex(selected.riskLevel)} fill="url(#rg2)" strokeWidth={1.5} dot={false} />
                              </AreaChart>
                            </ResponsiveContainer>
                          ) : <p className="text-xs text-slate-500">No prediction history.</p>}
                        </CardBody>
                      </Card>
                    </motion.div>
                  ) : (
                    <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                      className="h-48 flex flex-col items-center justify-center gap-2 bg-slate-900 border border-slate-800 rounded-xl">
                      <User size={28} className="text-slate-700" />
                      <p className="text-xs text-slate-500">Select a patient to view details</p>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Recent alerts */}
                {alerts.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-1.5">
                        <CalendarClock size={13} className="text-slate-500" /> Recent Alerts
                      </CardTitle>
                    </CardHeader>
                    <div className="divide-y divide-slate-800/60">
                      {alerts.slice(0,5).map((a, i) => (
                        <div key={i} className="flex items-start gap-3 px-5 py-3">
                          <ShieldAlert size={13} className="text-rose-400 mt-0.5 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-[10px] text-slate-500">{a.patientName}</p>
                            <p className="text-xs text-slate-400 leading-snug truncate">{a.message}</p>
                          </div>
                          <span className="text-[9px] text-slate-600 flex-shrink-0">{new Date(a.timestamp).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
              </div>
            </div>
          </motion.div>
        )}

        {/* TASKS */}
        {activeTab === 'tasks' && (
          <motion.div key="tsk" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <Card className="mb-4">
              <CardBody>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-slate-200">Shift Progress</span>
                  <span className="text-xs text-slate-500">{completedTasks}/{tasks.length} completed</span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full transition-all" style={{ width: `${tasks.length ? (completedTasks/tasks.length)*100 : 0}%` }} />
                </div>
              </CardBody>
            </Card>

            <div className="space-y-2">
              {tasks.map(t => {
                const Icon = taskIcon(t.type);
                return (
                  <motion.div key={t.id} layout>
                    <Card className={`transition-opacity ${t.done ? 'opacity-50' : ''}`}>
                      <CardBody className="flex items-center gap-4 py-3">
                        <button
                          onClick={() => toggleTask(t.id)}
                          className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 border-2 transition-all
                            ${t.done ? 'bg-emerald-500 border-emerald-500' : 'border-slate-600 hover:border-emerald-500'}`}
                        >
                          {t.done && <span className="text-white text-[10px] font-bold">✓</span>}
                        </button>
                        <Icon size={15} className={`flex-shrink-0 ${t.priority === 'critical' ? 'text-rose-400' : t.priority === 'high' ? 'text-orange-400' : 'text-slate-500'}`} />
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm font-medium text-slate-200 ${t.done ? 'line-through' : ''}`}>{t.task}</p>
                          <p className="text-xs text-slate-500 mt-0.5">{t.patient} · {t.bed}</p>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <p className="text-xs font-mono text-slate-400">{t.time}</p>
                          {t.priority === 'critical' && <Badge variant="critical" className="mt-1 text-[9px]">Urgent</Badge>}
                        </div>
                      </CardBody>
                    </Card>
                  </motion.div>
                );
              })}
              {tasks.length === 0 && <Card><CardBody className="text-sm text-slate-500">No tasks assigned.</CardBody></Card>}
            </div>
          </motion.div>
        )}

        {/* LAB ENTRY */}
        {activeTab === 'labs' && (
          <motion.div key="lab" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            {/* Mode toggle */}
            <div className="flex gap-2 mb-4">
              {[['manual','Manual Entry',FileText],['upload','Upload PDF',Upload]].map(([k,l,Ic]) => (
                <button key={k} onClick={() => setLabMode(k)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition-all
                    ${labMode === k ? 'bg-brand-500/10 border-brand-500/30 text-brand-400' : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300'}`}>
                  <Ic size={14} />{l}
                </button>
              ))}
            </div>

            {labMode === 'manual' ? (
              <Card>
                <CardBody>
                  <div className="max-w-xs mb-6">
                    <Select label="Patient" value={manualPid} onChange={e => setManualPid(e.target.value)}>
                      <option value="">— Select Patient —</option>
                      {admitted.map(p => <option key={p.id} value={p.id}>{p.name} ({p.bed})</option>)}
                    </Select>
                  </div>
                  <div className="grid grid-cols-4 gap-4">
                    {LAB_FIELDS.map(f => (
                      <div key={f.key} className="flex flex-col gap-1.5">
                        <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">{f.label}</label>
                        <input
                          type="number" step="any"
                          placeholder={f.range}
                          value={labForm[f.key] || ''}
                          onChange={e => setLabForm(p => ({ ...p, [f.key]: e.target.value }))}
                          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-brand-500 transition-colors"
                        />
                        <span className="text-[10px] text-slate-600">Ref: {f.range} {f.unit}</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-end mt-6">
                    <Button onClick={handleManualSubmit} disabled={!manualPid}>Submit Lab Results</Button>
                  </div>
                </CardBody>
              </Card>
            ) : (
              <Card>
                <CardBody>
                  <div className="max-w-xs mb-6">
                    <Select label="Patient" value={uploadPid} onChange={e => setUploadPid(e.target.value)}>
                      <option value="">— Select Patient —</option>
                      {admitted.map(p => <option key={p.id} value={p.id}>{p.name} ({p.bed})</option>)}
                    </Select>
                  </div>
                  <div
                    className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer
                      ${uploadPid ? 'border-slate-700 hover:border-brand-500/50 hover:bg-brand-500/4' : 'border-slate-800 opacity-50 cursor-not-allowed'}`}
                    onClick={() => uploadPid && fileRef.current?.click()}
                  >
                    <input type="file" ref={fileRef} className="hidden" accept=".pdf,image/*" onChange={handleUpload} />
                    <Upload size={32} className="mx-auto text-slate-600 mb-3" />
                    <h4 className="text-sm font-semibold text-slate-300 mb-1">Drop lab report PDF or click to browse</h4>
                    <p className="text-xs text-slate-500">{uploadPid ? 'OCR will extract lab values automatically' : 'Select a patient first'}</p>
                    {uploadProgress !== null && (
                      <div className="mt-4">
                        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div className="h-full bg-brand-500 transition-all rounded-full" style={{ width: `${Math.min(uploadProgress, 100)}%` }} />
                        </div>
                        <p className="text-xs text-slate-400 mt-2">
                          {uploadProgress >= 100
                            ? `✓ OCR complete — ${extractedCount} results extracted`
                            : `Scanning... ${Math.round(Math.min(uploadProgress, 99))}%`}
                        </p>
                      </div>
                    )}
                  </div>
                </CardBody>
              </Card>
            )}
          </motion.div>
        )}

        {/* ALERTS (read-only) */}
        {activeTab === 'alerts' && (
          <motion.div key="alt" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 mb-4">
              <Eye size={14} className="text-brand-400 flex-shrink-0" />
              <p className="text-xs text-slate-400">Alerts are <strong className="text-slate-200">read-only</strong> for nursing staff. Contact the attending physician to acknowledge.</p>
            </div>
            {alerts.length > 0 ? (
              <div className="space-y-3">
                {alerts.map(a => (
                  <Card key={a.id}>
                    <CardBody className="flex items-start gap-4">
                      <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${a.level === 'critical' ? 'bg-rose-500 shadow-[0_0_6px_rgba(244,63,94,0.8)]' : 'bg-orange-500'}`} />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1.5">
                          <Badge variant={a.level === 'critical' ? 'critical' : 'high'}>{a.title}</Badge>
                          <span className="text-xs text-slate-500">{a.patientName} · {a.bed}</span>
                        </div>
                        <p className="text-sm text-slate-400">{a.message}</p>
                        <p className="text-xs text-slate-600 mt-1">{new Date(a.timestamp).toLocaleString()}</p>
                      </div>
                      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700">
                        <ShieldAlert size={13} className={a.level === 'critical' ? 'text-rose-400' : 'text-orange-400'} />
                        <span className="text-xs text-slate-500">Pending</span>
                      </div>
                    </CardBody>
                  </Card>
                ))}
              </div>
            ) : (
              <Card><CardBody className="text-sm text-slate-500">No active alerts.</CardBody></Card>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function isAb(key, val) {
  const r = VITAL_RANGES[key];
  if (!r || val == null) return false;
  return val < r.min || val > r.max;
}
