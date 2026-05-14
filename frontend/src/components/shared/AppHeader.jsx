import { Activity, Bell, LogOut } from 'lucide-react';
import { useAppStore } from '../../store/appStore';

export function AppHeader({ role, onLogout }) {
  const user = useAppStore(s => s.user);
  const alerts = useAppStore(s => s.alerts);

  const name = user?.full_name || user?.username || (role === 'physician' ? 'Dr. Smith' : 'Nurse Jane');
  const roleLabel = role === 'physician' ? 'Attending Physician' : 'Nursing Unit';
  const initials = name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();

  return (
    <header className="sticky top-0 z-40 h-14 bg-void-950/90 backdrop-blur-md border-b border-slate-800/60 flex items-center justify-between px-6">
      {/* Left */}
      <div className="flex items-center gap-3">
        <div className="w-7 h-7 bg-brand-600 rounded-lg flex items-center justify-center shadow-lg shadow-brand-600/30">
          <Activity size={14} className="text-white" strokeWidth={2.5} />
        </div>
        <span className="font-bold text-slate-100 tracking-tight">ARISE</span>
        <div className="w-px h-4 bg-slate-800" />
        <span className="text-xs text-slate-500 font-medium">{roleLabel}</span>
      </div>

      {/* Right */}
      <div className="flex items-center gap-3">
        {alerts.length > 0 && (
          <div className="flex items-center gap-1.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 px-2.5 py-1 rounded-full text-xs font-semibold animate-pulse-slow">
            <Bell size={12} />
            {alerts.length} alert{alerts.length > 1 ? 's' : ''}
          </div>
        )}

        <div className="flex items-center gap-2.5">
          <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white
            ${role === 'physician' ? 'bg-brand-600 ring-2 ring-brand-600/30' : 'bg-emerald-600 ring-2 ring-emerald-600/30'}`}>
            {initials}
          </div>
          <div className="hidden sm:flex flex-col">
            <span className="text-xs font-semibold text-slate-200 leading-tight">{name}</span>
            <span className="text-[10px] text-slate-500 leading-tight">{roleLabel}</span>
          </div>
        </div>

        <button
          onClick={onLogout}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
        >
          <LogOut size={13} />
          Sign out
        </button>
      </div>
    </header>
  );
}
