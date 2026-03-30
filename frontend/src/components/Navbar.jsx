import { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useNotificationSound } from '../hooks/useNotificationSound';
import api from '../api/client';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState(0);
  const [prevUnread, setPrevUnread] = useState(0);
  const { playSound, isSoundEnabled, toggleSound } = useNotificationSound();
  const [soundOn, setSoundOn] = useState(true);

  useEffect(() => {
    setSoundOn(isSoundEnabled());
  }, []);

  useEffect(() => {
    if (!user) return;
    const fetchAlerts = () => {
      api.get('/alerts/unread/count')
        .then(r => {
          const newCount = r.data.unread_count;
          // Play sound if new alerts arrived
          if (newCount > prevUnread && prevUnread >= 0) {
            playSound();
          }
          setPrevUnread(newCount);
          setUnreadCount(newCount);
        })
        .catch(() => {});
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, [user, prevUnread, playSound]);

  if (!user) return null;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleSoundToggle = () => {
    const newState = toggleSound();
    setSoundOn(newState);
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
        <button
          className={`sound-toggle ${soundOn ? 'sound-on' : 'sound-off'}`}
          onClick={handleSoundToggle}
          title={soundOn ? 'Sound notifications ON' : 'Sound notifications OFF'}
        >
          {soundOn ? '🔊' : '🔇'}
        </button>
        <span className={`role-badge role-${user.role}`}>{user.role}</span>
        <span className="user-name">{user.full_name}</span>
        <button className="btn btn-sm btn-ghost" onClick={handleLogout}>Logout</button>
      </div>
    </nav>
  );
}
