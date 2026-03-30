import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';

export default function PatientsListPage() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    try {
      const res = await api.get('/patients/', { params: { status_filter: 'active' } });
      setPatients(res.data);
    } catch (err) {
      console.error('Failed to load patients:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading patients...</div>;

  return (
    <div className="patients-list-page">
      <div className="page-header">
        <h1>Active Patients</h1>
        <div className="page-actions">
          <Link to="/patients/add" className="btn btn-primary">+ Add Patient</Link>
          <Link to="/history" className="btn btn-secondary">View History</Link>
        </div>
      </div>

      {patients.length === 0 ? (
        <div className="empty-state">
          <p>No active patients found.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Age</th>
                <th>Gender</th>
                <th>Bed</th>
                <th>Ward</th>
                <th>Doctor</th>
                <th>Admitted</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((patient) => (
                <tr key={patient.patient_id}>
                  <td>#{patient.patient_id}</td>
                  <td className="patient-name">{patient.full_name}</td>
                  <td>{patient.age || '—'}</td>
                  <td>{patient.gender || '—'}</td>
                  <td>{patient.bed_number || '—'}</td>
                  <td>{patient.ward_name || '—'}</td>
                  <td>{patient.doctor_name || 'Unassigned'}</td>
                  <td>{patient.admission_time ? new Date(patient.admission_time).toLocaleDateString() : '—'}</td>
                  <td>
                    <span className={`status-badge status-${patient.status}`}>
                      {patient.status}
                    </span>
                  </td>
                  <td>
                    <Link to={`/patients/${patient.patient_id}`} className="btn btn-sm btn-link">
                      Details
                    </Link>
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
