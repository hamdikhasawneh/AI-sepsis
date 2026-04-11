import { Activity, Bell, LogOut } from 'lucide-react';

export default function SharedHeader({ role, onLogout }) {
  const name = role === 'physician' ? 'Dr. James Rivera' : 'Nurse Station A';
  const initials = role === 'physician' ? 'JR' : 'NS';

  return (
    <header className="shared-header">
      <div className="header-left">
        <Activity size={22} className="header-logo-icon" />
        <span className="header-logo">SepsisAI</span>
      </div>

      <div className="header-right">
        <button className="header-notif" aria-label="Notifications">
          <Bell size={18} />
          <span className="header-notif-badge" />
        </button>

        <div className="header-user">
          <div className="header-avatar">{initials}</div>
          <div className="header-user-info">
            <span className="header-user-name">{name}</span>
            <span className="header-user-role">{role === 'physician' ? 'Attending Physician' : 'Nursing Unit'}</span>
          </div>
        </div>

        <button className="header-logout" onClick={onLogout}>
          <LogOut size={14} />
          Logout
        </button>
      </div>
    </header>
  );
}
