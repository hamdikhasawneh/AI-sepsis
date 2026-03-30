import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';

export default function HistoryPage() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const res = await api.get('/patients/', { params: { status_filter: 'history' } });
      setPatients(res.data);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading history...</div>;

  return (
    <div className="history-page">
      <div className="page-header">
        <h1>Patient History</h1>
        <Link to="/patients" className="btn btn-secondary">← Active Patients</Link>
      </div>

      {patients.length === 0 ? (
        <div className="empty-state">
          <p>No discharged or transferred patients.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Age</th>
                <th>Bed</th>
                <th>Doctor</th>
                <th>Status</th>
                <th>Discharged/Transferred</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((patient) => (
                <tr key={patient.patient_id}>
                  <td className="patient-name">{patient.full_name}</td>
                  <td>{patient.age || '—'}</td>
                  <td>{patient.bed_number || '—'}</td>
                  <td>{patient.doctor_name || '—'}</td>
                  <td>
                    <span className={`status-badge status-${patient.status}`}>
                      {patient.status}
                    </span>
                  </td>
                  <td>{patient.discharge_time ? new Date(patient.discharge_time).toLocaleDateString() : '—'}</td>
                  <td>
                    <Link to={`/patients/${patient.patient_id}`} className="btn btn-sm btn-link">View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
