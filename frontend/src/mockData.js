// ═══════════════════════════════════════════════════════════════
//  Mock Data — AI Sepsis ICU Monitoring System
// ═══════════════════════════════════════════════════════════════

// Helper: generate time-series data points for the last N hours
function generateTimeSeries(hours, baseFn, noise = 5) {
  const now = new Date();
  const points = [];
  for (let i = hours * 4; i >= 0; i--) {
    const t = new Date(now.getTime() - i * 15 * 60000);
    points.push({
      time: t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      timestamp: t.toISOString(),
      value: Math.round((baseFn(i) + (Math.random() - 0.5) * noise) * 10) / 10,
    });
  }
  return points;
}

// ── Patients ──
export const patients = [
  {
    id: 'P-1001',
    name: 'Sarah Mitchell',
    age: 67,
    gender: 'Female',
    bed: 'ICU-4A',
    ward: 'ICU',
    admitDate: '2026-04-08',
    sepsisScore: 82,
    riskLevel: 'critical',
    doctor: 'Dr. James Rivera',
    diagnosis: 'Community-acquired pneumonia, suspected sepsis',
  },
  {
    id: 'P-1002',
    name: 'Ahmed Al-Rashid',
    age: 54,
    gender: 'Male',
    bed: 'ICU-2B',
    ward: 'ICU',
    admitDate: '2026-04-09',
    sepsisScore: 71,
    riskLevel: 'critical',
    doctor: 'Dr. Emily Chen',
    diagnosis: 'Post-surgical abdominal infection',
  },
  {
    id: 'P-1003',
    name: 'Maria Gonzalez',
    age: 45,
    gender: 'Female',
    bed: 'ICU-6C',
    ward: 'ICU',
    admitDate: '2026-04-07',
    sepsisScore: 55,
    riskLevel: 'high',
    doctor: 'Dr. James Rivera',
    diagnosis: 'Urinary tract infection with systemic inflammation',
  },
  {
    id: 'P-1004',
    name: 'James O\'Brien',
    age: 72,
    gender: 'Male',
    bed: 'ICU-1A',
    ward: 'ICU',
    admitDate: '2026-04-10',
    sepsisScore: 48,
    riskLevel: 'high',
    doctor: 'Dr. Emily Chen',
    diagnosis: 'Chronic obstructive pulmonary disease exacerbation',
  },
  {
    id: 'P-1005',
    name: 'Yuki Tanaka',
    age: 38,
    gender: 'Female',
    bed: 'ICU-3B',
    ward: 'ICU',
    admitDate: '2026-04-10',
    sepsisScore: 28,
    riskLevel: 'safe',
    doctor: 'Dr. James Rivera',
    diagnosis: 'Post-cardiac surgery monitoring',
  },
  {
    id: 'P-1006',
    name: 'Robert Williams',
    age: 61,
    gender: 'Male',
    bed: 'ICU-5A',
    ward: 'ICU',
    admitDate: '2026-04-09',
    sepsisScore: 15,
    riskLevel: 'safe',
    doctor: 'Dr. Emily Chen',
    diagnosis: 'Recovering from septic shock — improving',
  },
  {
    id: 'P-1007',
    name: 'Fatima Hassan',
    age: 50,
    gender: 'Female',
    bed: 'ICU-7A',
    ward: 'ICU',
    admitDate: '2026-04-06',
    sepsisScore: 62,
    riskLevel: 'high',
    doctor: 'Dr. James Rivera',
    diagnosis: 'Biliary sepsis secondary to cholangitis',
  },
  {
    id: 'P-1008',
    name: 'David Park',
    age: 29,
    gender: 'Male',
    bed: 'ICU-8B',
    ward: 'ICU',
    admitDate: '2026-04-11',
    sepsisScore: 22,
    riskLevel: 'safe',
    doctor: 'Dr. Emily Chen',
    diagnosis: 'Trauma — monitoring for infection',
  },
];

// ── Current Vitals (per patient) ──
export const currentVitals = {
  'P-1001': { hr: 118, bpSys: 85, bpDia: 52, spo2: 89, rr: 28, temp: 39.4, lactate: 4.8 },
  'P-1002': { hr: 112, bpSys: 90, bpDia: 55, spo2: 91, rr: 26, temp: 38.9, lactate: 3.9 },
  'P-1003': { hr: 102, bpSys: 95, bpDia: 60, spo2: 93, rr: 22, temp: 38.5, lactate: 2.8 },
  'P-1004': { hr: 98, bpSys: 100, bpDia: 65, spo2: 94, rr: 20, temp: 38.1, lactate: 2.2 },
  'P-1005': { hr: 78, bpSys: 120, bpDia: 75, spo2: 98, rr: 16, temp: 36.8, lactate: 1.0 },
  'P-1006': { hr: 72, bpSys: 125, bpDia: 80, spo2: 99, rr: 14, temp: 36.6, lactate: 0.8 },
  'P-1007': { hr: 105, bpSys: 92, bpDia: 58, spo2: 92, rr: 24, temp: 38.7, lactate: 3.2 },
  'P-1008': { hr: 80, bpSys: 118, bpDia: 72, spo2: 97, rr: 15, temp: 37.0, lactate: 1.1 },
};

// Normal ranges for vitals
export const vitalRanges = {
  hr: { min: 60, max: 100, unit: 'bpm', label: 'Heart Rate' },
  bpSys: { min: 90, max: 140, unit: 'mmHg', label: 'Systolic BP' },
  bpDia: { min: 60, max: 90, unit: 'mmHg', label: 'Diastolic BP' },
  spo2: { min: 95, max: 100, unit: '%', label: 'SpO2' },
  rr: { min: 12, max: 20, unit: '/min', label: 'Resp. Rate' },
  temp: { min: 36.1, max: 37.5, unit: '°C', label: 'Temperature' },
  lactate: { min: 0.5, max: 2.0, unit: 'mmol/L', label: 'Lactate' },
};

// ── Vital Trend Data (24h time-series per patient) ──
export function getVitalTrends(patientId) {
  const v = currentVitals[patientId];
  if (!v) return null;

  return {
    hr: generateTimeSeries(24, (i) => v.hr - (i * 0.15) + Math.sin(i / 8) * 8, 6),
    bpSys: generateTimeSeries(24, (i) => v.bpSys + (i * 0.1) + Math.sin(i / 10) * 5, 4),
    bpDia: generateTimeSeries(24, (i) => v.bpDia + (i * 0.05) + Math.cos(i / 10) * 3, 3),
    rr: generateTimeSeries(24, (i) => v.rr - (i * 0.08) + Math.sin(i / 6) * 3, 2),
    temp: generateTimeSeries(24, (i) => v.temp - (i * 0.005) + Math.sin(i / 12) * 0.3, 0.2),
    spo2: generateTimeSeries(24, (i) => Math.min(100, v.spo2 + (i * 0.02) + Math.cos(i / 8) * 1.5), 1),
  };
}

// ── Risk Trajectory (24h LSTM output) ──
export function getRiskTrajectory(patientId) {
  const patient = patients.find((p) => p.id === patientId);
  if (!patient) return [];
  const score = patient.sepsisScore;

  return generateTimeSeries(
    24,
    (i) => {
      const base = score - (i * 0.3);
      return Math.max(5, Math.min(95, base + Math.sin(i / 6) * 8));
    },
    4
  );
}

// ── Lab Results ──
export const labResults = {
  'P-1001': [
    { test: 'White Blood Cell Count', value: 18.5, unit: '×10³/µL', range: '4.5-11.0', status: 'critical' },
    { test: 'Serum Lactate', value: 4.8, unit: 'mmol/L', range: '0.5-2.0', status: 'critical' },
    { test: 'Procalcitonin', value: 8.2, unit: 'ng/mL', range: '<0.1', status: 'critical' },
    { test: 'C-Reactive Protein', value: 185, unit: 'mg/L', range: '<10', status: 'critical' },
    { test: 'Blood Glucose', value: 165, unit: 'mg/dL', range: '70-100', status: 'high' },
    { test: 'Creatinine', value: 2.1, unit: 'mg/dL', range: '0.6-1.2', status: 'critical' },
    { test: 'Hemoglobin', value: 10.2, unit: 'g/dL', range: '12.0-17.5', status: 'high' },
    { test: 'Platelet Count', value: 95, unit: '×10³/µL', range: '150-400', status: 'critical' },
    { test: 'Sodium', value: 138, unit: 'mEq/L', range: '136-145', status: 'normal' },
    { test: 'Potassium', value: 4.2, unit: 'mEq/L', range: '3.5-5.0', status: 'normal' },
  ],
  'P-1002': [
    { test: 'White Blood Cell Count', value: 16.2, unit: '×10³/µL', range: '4.5-11.0', status: 'critical' },
    { test: 'Serum Lactate', value: 3.9, unit: 'mmol/L', range: '0.5-2.0', status: 'critical' },
    { test: 'Procalcitonin', value: 5.6, unit: 'ng/mL', range: '<0.1', status: 'critical' },
    { test: 'C-Reactive Protein', value: 142, unit: 'mg/L', range: '<10', status: 'critical' },
    { test: 'Blood Glucose', value: 148, unit: 'mg/dL', range: '70-100', status: 'high' },
    { test: 'Creatinine', value: 1.8, unit: 'mg/dL', range: '0.6-1.2', status: 'high' },
    { test: 'Hemoglobin', value: 11.5, unit: 'g/dL', range: '12.0-17.5', status: 'high' },
    { test: 'Platelet Count', value: 120, unit: '×10³/µL', range: '150-400', status: 'high' },
    { test: 'Sodium', value: 141, unit: 'mEq/L', range: '136-145', status: 'normal' },
    { test: 'Potassium', value: 4.8, unit: 'mEq/L', range: '3.5-5.0', status: 'normal' },
  ],
  'P-1003': [
    { test: 'White Blood Cell Count', value: 13.8, unit: '×10³/µL', range: '4.5-11.0', status: 'high' },
    { test: 'Serum Lactate', value: 2.8, unit: 'mmol/L', range: '0.5-2.0', status: 'high' },
    { test: 'Procalcitonin', value: 2.1, unit: 'ng/mL', range: '<0.1', status: 'high' },
    { test: 'C-Reactive Protein', value: 78, unit: 'mg/L', range: '<10', status: 'high' },
    { test: 'Blood Glucose', value: 125, unit: 'mg/dL', range: '70-100', status: 'high' },
    { test: 'Creatinine', value: 1.3, unit: 'mg/dL', range: '0.6-1.2', status: 'high' },
    { test: 'Hemoglobin', value: 12.8, unit: 'g/dL', range: '12.0-17.5', status: 'normal' },
    { test: 'Platelet Count', value: 180, unit: '×10³/µL', range: '150-400', status: 'normal' },
    { test: 'Sodium', value: 139, unit: 'mEq/L', range: '136-145', status: 'normal' },
    { test: 'Potassium', value: 3.9, unit: 'mEq/L', range: '3.5-5.0', status: 'normal' },
  ],
  'P-1004': [
    { test: 'White Blood Cell Count', value: 12.5, unit: '×10³/µL', range: '4.5-11.0', status: 'high' },
    { test: 'Serum Lactate', value: 2.2, unit: 'mmol/L', range: '0.5-2.0', status: 'high' },
    { test: 'Procalcitonin', value: 1.4, unit: 'ng/mL', range: '<0.1', status: 'high' },
    { test: 'C-Reactive Protein', value: 52, unit: 'mg/L', range: '<10', status: 'high' },
    { test: 'Blood Glucose', value: 110, unit: 'mg/dL', range: '70-100', status: 'high' },
    { test: 'Creatinine', value: 1.0, unit: 'mg/dL', range: '0.6-1.2', status: 'normal' },
    { test: 'Hemoglobin', value: 13.5, unit: 'g/dL', range: '12.0-17.5', status: 'normal' },
    { test: 'Platelet Count', value: 210, unit: '×10³/µL', range: '150-400', status: 'normal' },
    { test: 'Sodium', value: 140, unit: 'mEq/L', range: '136-145', status: 'normal' },
    { test: 'Potassium', value: 4.1, unit: 'mEq/L', range: '3.5-5.0', status: 'normal' },
  ],
  'P-1005': [
    { test: 'White Blood Cell Count', value: 7.2, unit: '×10³/µL', range: '4.5-11.0', status: 'normal' },
    { test: 'Serum Lactate', value: 1.0, unit: 'mmol/L', range: '0.5-2.0', status: 'normal' },
    { test: 'Procalcitonin', value: 0.08, unit: 'ng/mL', range: '<0.1', status: 'normal' },
    { test: 'C-Reactive Protein', value: 5, unit: 'mg/L', range: '<10', status: 'normal' },
    { test: 'Blood Glucose', value: 92, unit: 'mg/dL', range: '70-100', status: 'normal' },
    { test: 'Creatinine', value: 0.9, unit: 'mg/dL', range: '0.6-1.2', status: 'normal' },
    { test: 'Hemoglobin', value: 14.1, unit: 'g/dL', range: '12.0-17.5', status: 'normal' },
    { test: 'Platelet Count', value: 245, unit: '×10³/µL', range: '150-400', status: 'normal' },
    { test: 'Sodium', value: 142, unit: 'mEq/L', range: '136-145', status: 'normal' },
    { test: 'Potassium', value: 4.0, unit: 'mEq/L', range: '3.5-5.0', status: 'normal' },
  ],
  'P-1006': [
    { test: 'White Blood Cell Count', value: 6.8, unit: '×10³/µL', range: '4.5-11.0', status: 'normal' },
    { test: 'Serum Lactate', value: 0.8, unit: 'mmol/L', range: '0.5-2.0', status: 'normal' },
    { test: 'Procalcitonin', value: 0.05, unit: 'ng/mL', range: '<0.1', status: 'normal' },
    { test: 'C-Reactive Protein', value: 3, unit: 'mg/L', range: '<10', status: 'normal' },
    { test: 'Blood Glucose', value: 88, unit: 'mg/dL', range: '70-100', status: 'normal' },
    { test: 'Creatinine', value: 0.8, unit: 'mg/dL', range: '0.6-1.2', status: 'normal' },
    { test: 'Hemoglobin', value: 14.5, unit: 'g/dL', range: '12.0-17.5', status: 'normal' },
    { test: 'Platelet Count', value: 280, unit: '×10³/µL', range: '150-400', status: 'normal' },
    { test: 'Sodium', value: 140, unit: 'mEq/L', range: '136-145', status: 'normal' },
    { test: 'Potassium', value: 4.3, unit: 'mEq/L', range: '3.5-5.0', status: 'normal' },
  ],
  'P-1007': [
    { test: 'White Blood Cell Count', value: 15.1, unit: '×10³/µL', range: '4.5-11.0', status: 'critical' },
    { test: 'Serum Lactate', value: 3.2, unit: 'mmol/L', range: '0.5-2.0', status: 'critical' },
    { test: 'Procalcitonin', value: 4.5, unit: 'ng/mL', range: '<0.1', status: 'critical' },
    { test: 'C-Reactive Protein', value: 120, unit: 'mg/L', range: '<10', status: 'critical' },
    { test: 'Blood Glucose', value: 135, unit: 'mg/dL', range: '70-100', status: 'high' },
    { test: 'Creatinine', value: 1.6, unit: 'mg/dL', range: '0.6-1.2', status: 'high' },
    { test: 'Hemoglobin', value: 11.0, unit: 'g/dL', range: '12.0-17.5', status: 'high' },
    { test: 'Platelet Count', value: 140, unit: '×10³/µL', range: '150-400', status: 'high' },
    { test: 'Sodium', value: 137, unit: 'mEq/L', range: '136-145', status: 'normal' },
    { test: 'Potassium', value: 4.5, unit: 'mEq/L', range: '3.5-5.0', status: 'normal' },
  ],
  'P-1008': [
    { test: 'White Blood Cell Count', value: 8.1, unit: '×10³/µL', range: '4.5-11.0', status: 'normal' },
    { test: 'Serum Lactate', value: 1.1, unit: 'mmol/L', range: '0.5-2.0', status: 'normal' },
    { test: 'Procalcitonin', value: 0.06, unit: 'ng/mL', range: '<0.1', status: 'normal' },
    { test: 'C-Reactive Protein', value: 8, unit: 'mg/L', range: '<10', status: 'normal' },
    { test: 'Blood Glucose', value: 95, unit: 'mg/dL', range: '70-100', status: 'normal' },
    { test: 'Creatinine', value: 0.9, unit: 'mg/dL', range: '0.6-1.2', status: 'normal' },
    { test: 'Hemoglobin', value: 15.2, unit: 'g/dL', range: '12.0-17.5', status: 'normal' },
    { test: 'Platelet Count', value: 310, unit: '×10³/µL', range: '150-400', status: 'normal' },
    { test: 'Sodium', value: 141, unit: 'mEq/L', range: '136-145', status: 'normal' },
    { test: 'Potassium', value: 4.2, unit: 'mEq/L', range: '3.5-5.0', status: 'normal' },
  ],
};

// Lab reference ranges for form inputs
export const labInputFields = [
  { key: 'wbc', label: 'WBC Count', unit: '×10³/µL', range: '4.5-11.0' },
  { key: 'lactate', label: 'Serum Lactate', unit: 'mmol/L', range: '0.5-2.0' },
  { key: 'procalcitonin', label: 'Procalcitonin', unit: 'ng/mL', range: '<0.1' },
  { key: 'crp', label: 'C-Reactive Protein', unit: 'mg/L', range: '<10' },
  { key: 'glucose', label: 'Blood Glucose', unit: 'mg/dL', range: '70-100' },
  { key: 'creatinine', label: 'Creatinine', unit: 'mg/dL', range: '0.6-1.2' },
  { key: 'hemoglobin', label: 'Hemoglobin', unit: 'g/dL', range: '12.0-17.5' },
  { key: 'platelets', label: 'Platelet Count', unit: '×10³/µL', range: '150-400' },
];

// ── Alerts ──
export const initialAlerts = [
  {
    id: 'ALT-001',
    patientId: 'P-1001',
    patientName: 'Sarah Mitchell',
    bed: 'ICU-4A',
    level: 'critical',
    title: 'Sepsis Score Exceeded Critical Threshold',
    message: 'AI model predicts 82% sepsis probability. Immediate clinical review required. Elevated lactate (4.8 mmol/L) and sustained tachycardia (HR 118) detected.',
    timestamp: '2026-04-11T19:45:00Z',
    vital_snapshot: { hr: 118, bpSys: 85, bpDia: 52 },
  },
  {
    id: 'ALT-002',
    patientId: 'P-1002',
    patientName: 'Ahmed Al-Rashid',
    bed: 'ICU-2B',
    level: 'critical',
    title: 'Rapid Deterioration Detected',
    message: 'Sepsis score increased by 18% in the last 2 hours. Post-surgical infection markers rising. Procalcitonin 5.6 ng/mL.',
    timestamp: '2026-04-11T19:30:00Z',
    vital_snapshot: { hr: 112, bpSys: 90, bpDia: 55 },
  },
  {
    id: 'ALT-003',
    patientId: 'P-1003',
    patientName: 'Maria Gonzalez',
    bed: 'ICU-6C',
    level: 'high',
    title: 'Elevated Inflammatory Markers',
    message: 'CRP rising trend detected over the last 6 hours. Current sepsis score: 55%. Consider broadening antibiotic coverage.',
    timestamp: '2026-04-11T18:15:00Z',
    vital_snapshot: { hr: 102, bpSys: 95, bpDia: 60 },
  },
  {
    id: 'ALT-004',
    patientId: 'P-1007',
    patientName: 'Fatima Hassan',
    bed: 'ICU-7A',
    level: 'high',
    title: 'Biliary Sepsis Indicators Worsening',
    message: 'Sustained fever (38.7°C) with elevated WBC (15.1). Lactate trending upward. AI score: 62%.',
    timestamp: '2026-04-11T17:50:00Z',
    vital_snapshot: { hr: 105, bpSys: 92, bpDia: 58 },
  },
  {
    id: 'ALT-005',
    patientId: 'P-1004',
    patientName: 'James O\'Brien',
    bed: 'ICU-1A',
    level: 'high',
    title: 'Respiratory Deterioration',
    message: 'Respiratory rate elevated (20/min), SpO2 trending down. Combined with fever, AI model suggests 48% sepsis risk.',
    timestamp: '2026-04-11T16:30:00Z',
    vital_snapshot: { hr: 98, bpSys: 100, bpDia: 65 },
  },
  {
    id: 'ALT-006',
    patientId: 'P-1001',
    patientName: 'Sarah Mitchell',
    bed: 'ICU-4A',
    level: 'critical',
    title: 'Renal Function Declining',
    message: 'Creatinine 2.1 mg/dL (rising from 1.5 12h ago). Combined with existing sepsis markers, risk of organ dysfunction increasing.',
    timestamp: '2026-04-11T15:00:00Z',
    vital_snapshot: { hr: 115, bpSys: 88, bpDia: 54 },
  },
];

// ── SHAP Feature Importance (per patient) ──
export const shapValues = {
  'P-1001': [
    { feature: 'Serum Lactate', impact: 0.82, direction: 'increase' },
    { feature: 'Heart Rate', impact: 0.71, direction: 'increase' },
    { feature: 'Procalcitonin', impact: 0.68, direction: 'increase' },
    { feature: 'Systolic BP', impact: -0.55, direction: 'decrease' },
    { feature: 'Platelet Count', impact: -0.48, direction: 'decrease' },
    { feature: 'WBC Count', impact: 0.45, direction: 'increase' },
    { feature: 'Temperature', impact: 0.38, direction: 'increase' },
    { feature: 'SpO2', impact: -0.35, direction: 'decrease' },
  ],
  'P-1002': [
    { feature: 'Procalcitonin', impact: 0.75, direction: 'increase' },
    { feature: 'Serum Lactate', impact: 0.65, direction: 'increase' },
    { feature: 'CRP', impact: 0.58, direction: 'increase' },
    { feature: 'Heart Rate', impact: 0.52, direction: 'increase' },
    { feature: 'Temperature', impact: 0.42, direction: 'increase' },
    { feature: 'Systolic BP', impact: -0.38, direction: 'decrease' },
    { feature: 'Creatinine', impact: 0.35, direction: 'increase' },
    { feature: 'SpO2', impact: -0.28, direction: 'decrease' },
  ],
  'P-1003': [
    { feature: 'CRP', impact: 0.55, direction: 'increase' },
    { feature: 'WBC Count', impact: 0.48, direction: 'increase' },
    { feature: 'Temperature', impact: 0.42, direction: 'increase' },
    { feature: 'Serum Lactate', impact: 0.35, direction: 'increase' },
    { feature: 'Heart Rate', impact: 0.28, direction: 'increase' },
    { feature: 'SpO2', impact: -0.22, direction: 'decrease' },
    { feature: 'Platelet Count', impact: 0.15, direction: 'increase' },
    { feature: 'Creatinine', impact: 0.12, direction: 'increase' },
  ],
  'P-1004': [
    { feature: 'Respiratory Rate', impact: 0.45, direction: 'increase' },
    { feature: 'Temperature', impact: 0.38, direction: 'increase' },
    { feature: 'WBC Count', impact: 0.32, direction: 'increase' },
    { feature: 'SpO2', impact: -0.28, direction: 'decrease' },
    { feature: 'Heart Rate', impact: 0.22, direction: 'increase' },
    { feature: 'Serum Lactate', impact: 0.18, direction: 'increase' },
    { feature: 'CRP', impact: 0.15, direction: 'increase' },
    { feature: 'Creatinine', impact: 0.08, direction: 'increase' },
  ],
  'P-1007': [
    { feature: 'Procalcitonin', impact: 0.62, direction: 'increase' },
    { feature: 'WBC Count', impact: 0.55, direction: 'increase' },
    { feature: 'Serum Lactate', impact: 0.48, direction: 'increase' },
    { feature: 'Temperature', impact: 0.42, direction: 'increase' },
    { feature: 'Heart Rate', impact: 0.35, direction: 'increase' },
    { feature: 'CRP', impact: 0.32, direction: 'increase' },
    { feature: 'Systolic BP', impact: -0.28, direction: 'decrease' },
    { feature: 'Platelet Count', impact: -0.22, direction: 'decrease' },
  ],
};

// Default SHAP for patients without specific data
const defaultShap = [
  { feature: 'Temperature', impact: 0.15, direction: 'increase' },
  { feature: 'Heart Rate', impact: 0.12, direction: 'increase' },
  { feature: 'WBC Count', impact: 0.10, direction: 'increase' },
  { feature: 'SpO2', impact: 0.08, direction: 'increase' },
  { feature: 'Lactate', impact: 0.05, direction: 'increase' },
  { feature: 'CRP', impact: 0.03, direction: 'increase' },
  { feature: 'Creatinine', impact: -0.02, direction: 'decrease' },
  { feature: 'Platelet Count', impact: 0.02, direction: 'increase' },
];

export function getShapValues(patientId) {
  return shapValues[patientId] || defaultShap;
}

// ── NLP Summaries ──
export const nlpSummaries = {
  'P-1001': 'Elevated serum lactate (4.8 mmol/L) combined with sustained tachycardia (HR 118 bpm) and hypotension (BP 85/52 mmHg) strongly indicate early septic shock. Procalcitonin levels (8.2 ng/mL) confirm active bacterial infection. The LSTM model identifies a rapidly escalating risk trajectory with 82% confidence. Immediate intervention with broad-spectrum antibiotics and fluid resuscitation is recommended.',
  'P-1002': 'Post-surgical inflammatory cascade detected with rising procalcitonin (5.6 ng/mL) and persistent fever (38.9°C). The AI model notes an 18% increase in sepsis probability over the past 2 hours, suggesting inadequate source control. Abdominal imaging and surgical consultation may be warranted. Current trajectory suggests progression to septic shock within 4-6 hours without intervention.',
  'P-1003': 'Moderate urinary tract infection with systemic inflammatory response. CRP trending upward (78 mg/L) with elevated WBC (13.8). The model identifies this as a HIGH risk case (55%) that could escalate if current antibiotic regimen is insufficient. Monitoring frequency should be increased to every 30 minutes.',
  'P-1004': 'COPD exacerbation with secondary infection markers. Respiratory rate elevated (20/min) with declining SpO2 (94%). Fever (38.1°C) and elevated lactate (2.2 mmol/L) suggest possible pneumonia-related sepsis developing. Current risk score: 48%. The model recommends close monitoring with consideration for ventilatory support.',
  'P-1007': 'Biliary sepsis secondary to cholangitis with progressive inflammatory markers. WBC 15.1, Procalcitonin 4.5 ng/mL. The model identifies sustained fever and tachycardia as primary risk drivers. Score has increased from 45% to 62% over 12 hours. Hepatobiliary drainage and antibiotic escalation should be considered.',
};

export function getNlpSummary(patientId) {
  return nlpSummaries[patientId] || 'The AI model indicates stable vital signs within acceptable parameters. No significant sepsis risk factors identified at this time. Continued standard monitoring is recommended with routine lab work as scheduled.';
}

// ── Model Confidence KPIs ──
export function getModelConfidence(patientId) {
  const patient = patients.find((p) => p.id === patientId);
  if (!patient) return { confidence: 0, sensitivity: 0, specificity: 0 };

  const score = patient.sepsisScore;
  return {
    confidence: Math.min(98, score + Math.round(Math.random() * 8)),
    sensitivity: score > 65 ? 94.2 : score > 40 ? 89.5 : 85.1,
    specificity: score > 65 ? 91.8 : score > 40 ? 93.2 : 96.4,
    auc: 0.942,
  };
}

// ── Shared Clinical Notes ──
export const initialNotes = [
  { id: 'N-001', patientId: 'P-1001', author: 'Dr. James Rivera', role: 'physician', text: 'Patient presenting with worsening septic shock indicators. Started Meropenem 1g IV q8h. Fluid resuscitation in progress — 2L NS bolus administered. Will reassess in 2 hours. Consider vasopressors if MAP remains <65.', timestamp: '2026-04-11T18:30:00Z' },
  { id: 'N-002', patientId: 'P-1001', author: 'Nurse Station A', role: 'nurse', text: 'Vitals recorded: HR 118, BP 85/52, SpO2 89%, Temp 39.4°C. Patient responsive but lethargic. IV access confirmed bilateral. Urine output 25mL/hr — below target. Notified Dr. Rivera.', timestamp: '2026-04-11T19:15:00Z' },
  { id: 'N-003', patientId: 'P-1002', author: 'Dr. Emily Chen', role: 'physician', text: 'Post-surgical wound showing signs of infection. Ordered CT abdomen to rule out abscess. Escalating antibiotics to Piperacillin/Tazobactam. Surgical consultation requested for possible washout.', timestamp: '2026-04-11T17:45:00Z' },
  { id: 'N-004', patientId: 'P-1002', author: 'Nurse Station A', role: 'nurse', text: 'Dressing changed — noted purulent drainage from surgical site. Wound culture sent. Patient reports increased abdominal pain (7/10). Administered Morphine 4mg IV per PRN order.', timestamp: '2026-04-11T18:00:00Z' },
  { id: 'N-005', patientId: 'P-1003', author: 'Dr. James Rivera', role: 'physician', text: 'UTI with SIRS criteria met. Current antibiotics may be insufficient given rising CRP. Switching to Ertapenem. Recheck labs in 6 hours. Monitoring for hemodynamic instability.', timestamp: '2026-04-11T16:20:00Z' },
  { id: 'N-006', patientId: 'P-1007', author: 'Dr. James Rivera', role: 'physician', text: 'Biliary sepsis progressing despite current regimen. Requesting ERCP consult for biliary drainage. Added Metronidazole for anaerobic coverage. Monitor LFTs closely.', timestamp: '2026-04-11T15:30:00Z' },
  { id: 'N-007', patientId: 'P-1007', author: 'Nurse Station A', role: 'nurse', text: 'Patient spiked fever 38.7°C at 15:00. Blood cultures drawn x2 (peripheral + central line). Cooling measures initiated. IV fluids running at 125mL/hr.', timestamp: '2026-04-11T15:45:00Z' },
  { id: 'N-008', patientId: 'P-1005', author: 'Nurse Station A', role: 'nurse', text: 'Post-cardiac surgery day 2. Ambulated with assistance x1. Tolerating clear liquids. Chest tube output decreased to 50mL/shift. Incision clean and dry. Stable for continued recovery.', timestamp: '2026-04-11T14:00:00Z' },
];

// ── Shared Tasks ──
export const initialTasks = [
  { id: 1, patient: 'Sarah Mitchell', bed: 'ICU-4A', patientId: 'P-1001', task: 'Administer IV Meropenem 1g', time: '21:00', type: 'medication', priority: 'critical', done: false },
  { id: 2, patient: 'Ahmed Al-Rashid', bed: 'ICU-2B', patientId: 'P-1002', task: 'Blood culture collection', time: '21:15', type: 'lab', priority: 'critical', done: false },
  { id: 3, patient: 'Sarah Mitchell', bed: 'ICU-4A', patientId: 'P-1001', task: 'Fluid bolus — Normal Saline 500mL', time: '21:30', type: 'medication', priority: 'critical', done: false },
  { id: 4, patient: 'Maria Gonzalez', bed: 'ICU-6C', patientId: 'P-1003', task: 'Record hourly vitals', time: '22:00', type: 'vitals', priority: 'high', done: false },
  { id: 5, patient: 'Fatima Hassan', bed: 'ICU-7A', patientId: 'P-1007', task: 'Administer IV Piperacillin', time: '22:00', type: 'medication', priority: 'high', done: false },
  { id: 6, patient: 'James O\'Brien', bed: 'ICU-1A', patientId: 'P-1004', task: 'Nebulizer treatment', time: '22:30', type: 'medication', priority: 'medium', done: false },
  { id: 7, patient: 'Yuki Tanaka', bed: 'ICU-3B', patientId: 'P-1005', task: 'Post-op wound assessment', time: '23:00', type: 'assessment', priority: 'medium', done: false },
  { id: 8, patient: 'David Park', bed: 'ICU-8B', patientId: 'P-1008', task: 'DVT prophylaxis injection', time: '23:00', type: 'medication', priority: 'medium', done: false },
  { id: 9, patient: 'Robert Williams', bed: 'ICU-5A', patientId: 'P-1006', task: 'Discharge vitals & documentation', time: '23:30', type: 'vitals', priority: 'low', done: false },
];
