import { useState, useEffect } from 'react';
import api from '../api/client';

export default function AdminUsersPage() {
  const [users, setUsers] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    username: '', email: '', password: '', full_name: '', role: 'nurse',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const res = await api.get('/users/');
      setUsers(res.data);
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      await api.post('/users/', form);
      setShowForm(false);
      setForm({ username: '', email: '', password: '', full_name: '', role: 'nurse' });
      loadUsers();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create user');
    }
  };

  const toggleActive = async (userId, currentStatus) => {
    try {
      await api.patch(`/users/${userId}`, { is_active: !currentStatus });
      loadUsers();
    } catch (err) {
      console.error('Failed to update user:', err);
    }
  };

  if (loading) return <div className="loading">Loading users...</div>;

  return (
    <div className="admin-users-page">
      <div className="page-header">
        <h1>User Management</h1>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ Add User'}
        </button>
      </div>

      {showForm && (
        <div className="form-card">
          <h2>Create New User</h2>
          {error && <div className="alert alert-error">{error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="new_full_name">Full Name *</label>
                <input id="new_full_name" name="full_name" value={form.full_name} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label htmlFor="new_username">Username *</label>
                <input id="new_username" name="username" value={form.username} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label htmlFor="new_email">Email *</label>
                <input id="new_email" name="email" type="email" value={form.email} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label htmlFor="new_password">Password *</label>
                <input id="new_password" name="password" type="password" value={form.password} onChange={handleChange} required />
              </div>
              <div className="form-group">
                <label htmlFor="new_role">Role *</label>
                <select id="new_role" name="role" value={form.role} onChange={handleChange}>
                  <option value="nurse">Nurse</option>
                  <option value="doctor">Doctor</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary">Create User</button>
            </div>
          </form>
        </div>
      )}

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.user_id}>
                <td>#{u.user_id}</td>
                <td>{u.full_name}</td>
                <td>{u.username}</td>
                <td>{u.email}</td>
                <td>
                  <span className={`role-badge role-${u.role}`}>{u.role}</span>
                </td>
                <td>
                  <span className={`status-badge ${u.is_active ? 'status-admitted' : 'status-discharged'}`}>
                    {u.is_active ? 'Active' : 'Disabled'}
                  </span>
                </td>
                <td>
                  <button
                    className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-primary'}`}
                    onClick={() => toggleActive(u.user_id, u.is_active)}
                  >
                    {u.is_active ? 'Disable' : 'Enable'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
