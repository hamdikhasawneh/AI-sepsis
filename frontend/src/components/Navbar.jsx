import { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!user) return;
    const fetchAlerts = () => {
      api.get('/alerts/unread/count')
        .then(r => setUnreadCount(r.data.unread_count))
        .catch(() => {});
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, [user]);

  if (!user) return null;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path ? 'nav-link active' : 'nav-link';

  return (
    <nav className="navbar">
      <div className="nav-brand">
        <Link to="/dashboard">
          <span className="nav-icon">🏥</span>
          <span className="nav-title">Sepsis ICU</span>
        </Link>
      </div>

      <div className="nav-links">
        <Link to="/dashboard" className={isActive('/dashboard')}>Dashboard</Link>
        <Link to="/patients" className={isActive('/patients')}>Patients</Link>
        <Link to="/history" className={isActive('/history')}>History</Link>

        <Link to="/alerts" className={isActive('/alerts')}>
          🔔 Alerts
          {unreadCount > 0 && <span className="alert-count-badge">{unreadCount}</span>}
        </Link>

        {(user.role === 'nurse' || user.role === 'admin') && (
          <Link to="/vitals/add" className={isActive('/vitals/add')}>Record Vitals</Link>
        )}

        {user.role === 'admin' && (
          <>
            <Link to="/admin/users" className={isActive('/admin/users')}>Users</Link>
            <Link to="/admin/settings" className={isActive('/admin/settings')}>Settings</Link>
          </>
        )}
      </div>

      <div className="nav-user">
        <span className={`role-badge role-${user.role}`}>{user.role}</span>
        <span className="user-name">{user.full_name}</span>
        <button className="btn btn-sm btn-ghost" onClick={handleLogout}>Logout</button>
      </div>
    </nav>
  );
}
