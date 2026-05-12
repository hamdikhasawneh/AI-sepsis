import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const API_BASE = 'http://localhost:8000/api';

export const authFetch = (url, options = {}) => {
  const token = localStorage.getItem('sepsis_token');
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
};

function normRiskLevel(level) {
  if (level === 'critical') return 'critical';
  if (level === 'high_risk' || level === 'high') return 'high';
  return 'safe';
}

function normPatient(p, pred, vital) {
  const riskScore = pred ? Math.round(pred.risk_score * 100) : 0;
  const riskLevel = pred ? normRiskLevel(pred.risk_level) : 'safe';
  return {
    id: p.patient_id,
    name: p.full_name,
    age: p.age,
    gender: p.gender ? p.gender.charAt(0).toUpperCase() + p.gender.slice(1) : '',
    bed: p.bed_number,
    ward: p.ward_name,
    admitDate: p.admission_time
      ? new Date(p.admission_time).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
      : '',
    sepsisScore: riskScore,
    riskLevel,
    diagnosis: p.diagnosis_notes || '',
    status: p.status,
    simulationHour: p.simulation_hour || null,
    latestVitals: vital ? {
      hr: vital.heart_rate,
      rr: vital.respiratory_rate,
      temp: vital.temperature,
      spo2: vital.spo2,
      bpSys: vital.systolic_bp,
      bpDia: vital.diastolic_bp,
    } : null,
  };
}

export const useAppStore = create(
  persist(
    (set, get) => ({
      // Auth
      user: null,
      token: null,
      
      // UI
      isSimulationPanelOpen: false,

      // Data
      patients: [],
      alerts: [],
      tasks: [],
      labs: {},
      selectedPatientId: null,

      // UI
      setSimulationPanelOpen: (isOpen) => set({ isSimulationPanelOpen: isOpen }),
      setSelectedPatientId: (id) => set({ selectedPatientId: id }),
      
      setAuth: (user, token) => {
        localStorage.setItem('sepsis_token', token);
        set({ user, token });
      },

      clearAuth: () => {
        localStorage.removeItem('sepsis_token');
        set({ user: null, token: null, patients: [], alerts: [], tasks: [], labs: {} });
      },

      validateSession: async () => {
        const { token } = get();
        if (!token) return false;
        try {
          const res = await fetch(`${API_BASE}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (res.ok) {
            const user = await res.json();
            set({ user });
            return true;
          }
        } catch (_) {}
        get().clearAuth();
        return false;
      },

      // ── Fetch all ─────────────────────────────────────────
      // Uses /api/patients/summary — one call returns patients+latest prediction+latest vital
      fetchAll: async () => {
        try {
          // Single batch call replaces N×2 individual prediction+vital calls
          const sRes = await authFetch(`${API_BASE}/patients/summary`);
          if (!sRes.ok) return;
          const sData = await sRes.json();

          const normalizedPatients = sData.map(p =>
            normPatient(p, p.latest_prediction, p.latest_vital)
          );

          const [aRes, tRes, lRes] = await Promise.all([
            authFetch(`${API_BASE}/alerts/`),
            authFetch(`${API_BASE}/tasks/`),
            authFetch(`${API_BASE}/labs/`),
          ]);

          const aData = aRes.ok ? await aRes.json() : [];
          const alerts = aData
            .filter(a => !a.is_read)
            .map(a => ({
              id: a.alert_id,
              patientId: a.patient_id,
              patientName:
                normalizedPatients.find(p => p.id === a.patient_id)?.name ||
                `Patient ${a.patient_id}`,
              bed: normalizedPatients.find(p => p.id === a.patient_id)?.bed || '',
              title: a.alert_level === 'critical' ? 'CRITICAL SEPSIS RISK' : 'HIGH SEPSIS RISK',
              message: a.alert_message,
              level: a.alert_level,
              timestamp: a.created_at || new Date().toISOString(),
            }));

          const tData = tRes.ok ? await tRes.json() : [];
          const tasks = tData.map(t => {
            const pid = Number(t.patient_id);
            const pat = normalizedPatients.find(p => p.id === pid);
            return {
              id: t.task_id ?? t.id,
              patientId: pid,
              patient: pat?.name || `Patient ${t.patient_id}`,
              bed: pat?.bed || '',
              task: t.description,
              time: t.scheduled_time || '',
              type: t.task_type || 'assessment',
              priority: t.priority || 'medium',
              done: t.is_completed,
            };
          });

          const lData = lRes.ok ? await lRes.json() : [];
          const labsByPatient = {};
          lData.forEach(lab => {
            const pid = Number(lab.patient_id);
            if (!labsByPatient[pid]) labsByPatient[pid] = [];
            labsByPatient[pid].push({
              test: lab.test_name,
              value: lab.value,
              unit: lab.unit,
              range: lab.reference_range,
              status: lab.status,
            });
          });

          set({ patients: normalizedPatients, alerts, tasks, labs: labsByPatient });
        } catch (err) {
          console.error('fetchAll error:', err);
        }
      },

      // ── Alert actions ──────────────────────────────────────
      removeAlert: alertId =>
        set(s => ({ alerts: s.alerts.filter(a => a.id !== alertId) })),

      addWsAlert: alert =>
        set(s => ({ alerts: [alert, ...s.alerts] })),

      acknowledgeAlert: async alertId => {
        await authFetch(`${API_BASE}/alerts/${alertId}/read`, { method: 'PATCH' }).catch(() => null);
        set(s => ({ alerts: s.alerts.filter(a => a.id !== alertId) }));
      },

      // ── Task actions ───────────────────────────────────────
      // Lightweight re-fetch of tasks only (used for 10s polling in NurseScreen
      // so tasks created by doctors appear for nurses without a full reload).
      refreshTasks: async () => {
        const { patients } = get();
        try {
          const res = await authFetch(`${API_BASE}/tasks/`);
          if (!res.ok) return;
          const tData = await res.json();
          const tasks = tData.map(t => {
            const pid = Number(t.patient_id);
            const pat = patients.find(p => p.id === pid);
            return {
              id: t.task_id ?? t.id,
              patientId: pid,
              patient: pat?.name || `Patient ${t.patient_id}`,
              bed: pat?.bed || '',
              task: t.description,
              time: t.scheduled_time || '',
              type: t.task_type || 'assessment',
              priority: t.priority || 'medium',
              done: t.is_completed,
            };
          });
          set({ tasks });
        } catch (_) {}
      },

      toggleTask: async id => {
        const task = get().tasks.find(t => t.id === id);
        if (!task) return;
        const res = await authFetch(`${API_BASE}/tasks/${id}`, {
          method: 'PATCH',
          body: JSON.stringify({ is_completed: !task.done }),
        }).catch(() => null);
        if (res?.ok) {
          set(s => ({
            tasks: s.tasks.map(t => t.id === id ? { ...t, done: !t.done } : t),
          }));
        }
      },

      addTask: async taskInput => {
        const patients = get().patients;
        const res = await authFetch(`${API_BASE}/tasks/`, {
          method: 'POST',
          body: JSON.stringify({
            patient_id: String(taskInput.patientId),
            description: taskInput.task,
            scheduled_time: taskInput.time,
            task_type: taskInput.type,
            priority: taskInput.priority,
          }),
        }).catch(() => null);
        if (res?.ok) {
          const newTask = await res.json();
          const pid = Number(newTask.patient_id);
          const patient = patients.find(p => p.id === pid);
          set(s => ({
            tasks: [
              ...s.tasks,
              {
                id: newTask.task_id ?? newTask.id,
                patientId: pid,
                patient: patient?.name || `Patient ${newTask.patient_id}`,
                bed: patient?.bed || '',
                task: newTask.description,
                time: newTask.scheduled_time || taskInput.time,
                type: newTask.task_type || taskInput.type,
                priority: newTask.priority || taskInput.priority,
                done: false,
              },
            ],
          }));
        }
      },

      // ── Lab actions ────────────────────────────────────────
      addLab: async labData => {
        const pid = Number(labData.patient_id);
        const newLab = {
          test: labData.test_name,
          value: labData.value,
          unit: labData.unit,
          range: labData.reference_range,
          status: labData.status,
        };
        set(s => ({
          labs: {
            ...s.labs,
            [pid]: [newLab, ...(s.labs[pid] || []).filter(l => l.test !== newLab.test)],
          },
        }));
        await authFetch(`${API_BASE}/labs/`, {
          method: 'POST',
          body: JSON.stringify({ ...labData, patient_id: String(labData.patient_id) }),
        }).catch(() => null);
      },
    }),
    {
      name: 'sepsis-auth-v2',
      partialize: state => ({ 
        user: state.user, 
        token: state.token,
        patients: state.patients,
        alerts: state.alerts,
        tasks: state.tasks,
        labs: state.labs,
        selectedPatientId: state.selectedPatientId
      }),
    }
  )
);
