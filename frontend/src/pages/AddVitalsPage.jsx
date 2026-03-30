import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';

export default function AddVitalsPage() {
  const [patients, setPatients] = useState([]);
  const [form, setForm] = useState({
    patient_id: '',
    heart_rate: '',
    respiratory_rate: '',
    temperature: '',
    spo2: '',
    systolic_bp: '',
    diastolic_bp: '',
    mean_bp: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/patients/', { params: { status_filter: 'active' } })
      .then(res => setPatients(res.data))
      .catch(console.error);
  }, []);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const data = {};
      data.patient_id = parseInt(form.patient_id);
      data.source = 'manual';

      // Only include non-empty numeric fields
      const numericFields = ['heart_rate', 'respiratory_rate', 'temperature', 'spo2', 'systolic_bp', 'diastolic_bp', 'mean_bp'];
      for (const field of numericFields) {
        if (form[field]) {
          data[field] = parseFloat(form[field]);
        }
      }

      await api.post('/vitals/', data);
      setSuccess('Vital signs recorded successfully!');

      // Reset form but keep patient selected
      setForm(prev => ({
        ...prev,
        heart_rate: '',
        respiratory_rate: '',
        temperature: '',
        spo2: '',
        systolic_bp: '',
        diastolic_bp: '',
        mean_bp: '',
      }));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to record vitals');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-page">
      <div className="page-header">
        <h1>Record Vital Signs</h1>
      </div>

      <div className="form-card">
        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="patient_id">Patient *</label>
            <select id="patient_id" name="patient_id" value={form.patient_id} onChange={handleChange} required>
              <option value="">Select Patient</option>
              {patients.map(p => (
                <option key={p.patient_id} value={p.patient_id}>
                  {p.full_name} — Bed {p.bed_number || 'N/A'}
                </option>
              ))}
            </select>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="heart_rate">Heart Rate (bpm)</label>
              <input id="heart_rate" name="heart_rate" type="number" step="0.1" value={form.heart_rate} onChange={handleChange} placeholder="60-120" />
            </div>

            <div className="form-group">
              <label htmlFor="respiratory_rate">Respiratory Rate (/min)</label>
              <input id="respiratory_rate" name="respiratory_rate" type="number" step="0.1" value={form.respiratory_rate} onChange={handleChange} placeholder="12-30" />
            </div>

            <div className="form-group">
              <label htmlFor="temperature">Temperature (°C)</label>
              <input id="temperature" name="temperature" type="number" step="0.1" value={form.temperature} onChange={handleChange} placeholder="36.0-39.5" />
            </div>

            <div className="form-group">
              <label htmlFor="spo2">SpO2 (%)</label>
              <input id="spo2" name="spo2" type="number" step="0.1" value={form.spo2} onChange={handleChange} placeholder="90-100" />
            </div>

            <div className="form-group">
              <label htmlFor="systolic_bp">Systolic BP (mmHg)</label>
              <input id="systolic_bp" name="systolic_bp" type="number" step="0.1" value={form.systolic_bp} onChange={handleChange} placeholder="90-160" />
            </div>

            <div className="form-group">
              <label htmlFor="diastolic_bp">Diastolic BP (mmHg)</label>
              <input id="diastolic_bp" name="diastolic_bp" type="number" step="0.1" value={form.diastolic_bp} onChange={handleChange} placeholder="50-100" />
            </div>

            <div className="form-group">
              <label htmlFor="mean_bp">Mean BP (mmHg)</label>
              <input id="mean_bp" name="mean_bp" type="number" step="0.1" value={form.mean_bp} onChange={handleChange} placeholder="65-120" />
            </div>
          </div>

          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/dashboard')}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Recording...' : 'Record Vitals'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
