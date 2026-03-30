import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';

export default function AddPatientPage() {
  const [form, setForm] = useState({
    full_name: '',
    date_of_birth: '',
    age: '',
    gender: '',
    bed_number: '',
    ward_name: 'ICU',
    assigned_doctor_id: '',
    diagnosis_notes: '',
  });
  const [doctors, setDoctors] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/users/doctors').then(res => setDoctors(res.data)).catch(console.error);
  }, []);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = { ...form };
      if (data.age) data.age = parseInt(data.age);
      if (!data.date_of_birth) delete data.date_of_birth;
      if (!data.assigned_doctor_id) delete data.assigned_doctor_id;
      else data.assigned_doctor_id = parseInt(data.assigned_doctor_id);

      await api.post('/patients/', data);
      navigate('/patients');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add patient');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-page">
      <div className="page-header">
        <h1>Add New Patient</h1>
      </div>

      <div className="form-card">
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="full_name">Full Name *</label>
              <input id="full_name" name="full_name" value={form.full_name} onChange={handleChange} required />
            </div>

            <div className="form-group">
              <label htmlFor="date_of_birth">Date of Birth</label>
              <input id="date_of_birth" name="date_of_birth" type="date" value={form.date_of_birth} onChange={handleChange} />
            </div>

            <div className="form-group">
              <label htmlFor="age">Age</label>
              <input id="age" name="age" type="number" value={form.age} onChange={handleChange} />
            </div>

            <div className="form-group">
              <label htmlFor="gender">Gender</label>
              <select id="gender" name="gender" value={form.gender} onChange={handleChange}>
                <option value="">Select</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="bed_number">Bed Number</label>
              <input id="bed_number" name="bed_number" value={form.bed_number} onChange={handleChange} />
            </div>

            <div className="form-group">
              <label htmlFor="ward_name">Ward</label>
              <input id="ward_name" name="ward_name" value={form.ward_name} onChange={handleChange} />
            </div>

            <div className="form-group">
              <label htmlFor="assigned_doctor_id">Assigned Doctor</label>
              <select id="assigned_doctor_id" name="assigned_doctor_id" value={form.assigned_doctor_id} onChange={handleChange}>
                <option value="">Select Doctor</option>
                {doctors.map(d => (
                  <option key={d.user_id} value={d.user_id}>{d.full_name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group full-width">
            <label htmlFor="diagnosis_notes">Diagnosis Notes</label>
            <textarea id="diagnosis_notes" name="diagnosis_notes" rows={3} value={form.diagnosis_notes} onChange={handleChange} />
          </div>

          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/patients')}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Adding...' : 'Add Patient'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
