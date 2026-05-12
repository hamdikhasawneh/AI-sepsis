import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Stethoscope, HeartPulse, Eye, EyeOff, ArrowLeft, Lock, User, AlertCircle } from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

const API_BASE = 'http://localhost:8000/api';

const DEMO = {
  physician: { username: 'dr.smith',   password: 'doctor123' },
  nurse:     { username: 'nurse.jane', password: 'nurse123'  },
};

export default function LoginScreen({ onLogin, onBack }) {
  const setAuth = useAppStore(s => s.setAuth);
  const [role, setRole] = useState(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async e => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) { setError('Enter username and password'); return; }
    setError(''); setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (res.ok) {
        const data = await res.json();
        const meRes = await fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${data.access_token}` } });
        const user = await meRes.json();
        setAuth(user, data.access_token);
        onLogin(user.role === 'nurse' ? 'nurse' : 'physician');
      } else {
        const err = await res.json();
        setError(err.detail || 'Authentication failed');
      }
    } catch {
      setError('Connection error. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-void-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background blobs */}
      <div className="absolute top-1/4 right-1/4 w-[500px] h-[500px] bg-brand-600/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/4 w-[400px] h-[400px] bg-violet-600/4 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        className="relative z-10 w-full max-w-[420px]"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-brand-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-xl shadow-brand-600/30">
            <Activity size={22} className="text-white" strokeWidth={2.5} />
          </div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">ARISE</h1>
          <p className="text-sm text-slate-500 mt-1">ICU Intelligence Platform</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl shadow-black/30 overflow-hidden">
          <div className="absolute top-0 left-8 right-8 h-px bg-gradient-to-r from-transparent via-brand-500/30 to-transparent" />

          <div className="p-7">
            <AnimatePresence mode="wait">
              {/* Step 1: Role Selection */}
              {!role && (
                <motion.div
                  key="roles"
                  initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -16 }}
                  transition={{ duration: 0.25 }}
                >
                  {onBack && (
                    <button onClick={onBack} className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 mb-6 transition-colors">
                      <ArrowLeft size={13} /> Back to home
                    </button>
                  )}
                  <h2 className="text-base font-semibold text-slate-200 mb-1">Select your role</h2>
                  <p className="text-sm text-slate-500 mb-6">Choose how you'll access ARISE</p>

                  <div className="flex flex-col gap-3">
                    {[
                      { key: 'physician', icon: Stethoscope, label: 'Physician',    sub: 'Clinical analysis & AI reasoning',  accent: 'brand' },
                      { key: 'nurse',     icon: HeartPulse,  label: 'Nursing Unit', sub: 'Unit monitoring & alert triage',    accent: 'emerald' },
                    ].map(r => {
                      const Icon = r.icon;
                      return (
                        <button
                          key={r.key}
                          onClick={() => { setRole(r.key); setError(''); }}
                          className="flex items-center gap-4 p-4 rounded-xl border border-slate-800 hover:border-slate-600 bg-slate-800/40 hover:bg-slate-800/70 text-left transition-all group"
                        >
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0
                            ${r.accent === 'brand' ? 'bg-brand-500/12 text-brand-400 group-hover:bg-brand-500/20' : 'bg-emerald-500/12 text-emerald-400 group-hover:bg-emerald-500/20'}
                            transition-colors`}>
                            <Icon size={20} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-slate-200">{r.label}</p>
                            <p className="text-xs text-slate-500 mt-0.5">{r.sub}</p>
                          </div>
                          <ArrowLeft size={14} className="text-slate-600 rotate-180 group-hover:text-slate-400 transition-colors" />
                        </button>
                      );
                    })}
                  </div>
                </motion.div>
              )}

              {/* Step 2: Credentials */}
              {role && (
                <motion.div
                  key="creds"
                  initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -16 }}
                  transition={{ duration: 0.25 }}
                >
                  <button onClick={() => { setRole(null); setError(''); }} className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 mb-6 transition-colors">
                    <ArrowLeft size={13} /> Change role
                  </button>

                  <div className="flex items-center gap-3 mb-6">
                    {role === 'physician' ? <Stethoscope size={18} className="text-brand-400" /> : <HeartPulse size={18} className="text-emerald-400" />}
                    <h2 className="text-base font-semibold text-slate-200">
                      {role === 'physician' ? 'Physician Login' : 'Nurse Station Login'}
                    </h2>
                  </div>

                  {error && (
                    <motion.div
                      className="flex items-start gap-2.5 bg-rose-500/8 border border-rose-500/20 text-rose-400 rounded-lg px-3.5 py-3 text-sm mb-5"
                      initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
                    >
                      <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
                      {error}
                    </motion.div>
                  )}

                  <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                    <Input
                      label="Username"
                      type="text"
                      placeholder="Enter your username"
                      value={username}
                      onChange={e => setUsername(e.target.value)}
                      icon={User}
                      autoFocus
                      autoComplete="username"
                    />
                    <Input
                      label="Password"
                      type={showPw ? 'text' : 'password'}
                      placeholder="Enter your password"
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      icon={Lock}
                      autoComplete="current-password"
                      rightEl={
                        <button type="button" onClick={() => setShowPw(!showPw)} className="text-slate-500 hover:text-slate-300 transition-colors">
                          {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                      }
                    />

                    <Button type="submit" className="w-full justify-center mt-1" disabled={loading}>
                      {loading ? (
                        <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                      ) : 'Sign In'}
                    </Button>
                  </form>

                  {/* Demo credentials */}
                  <div className="mt-5 p-3.5 rounded-lg bg-slate-800/60 border border-slate-800">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Demo credentials</p>
                      <button
                        type="button"
                        onClick={() => { setUsername(DEMO[role].username); setPassword(DEMO[role].password); setError(''); }}
                        className="text-[10px] font-semibold text-brand-400 hover:text-brand-300 bg-brand-500/10 hover:bg-brand-500/20 px-2 py-0.5 rounded transition-all"
                      >
                        Fill
                      </button>
                    </div>
                    <div className="flex gap-4 text-xs">
                      <div>
                        <span className="text-slate-500">User </span>
                        <code className="text-slate-300 font-mono">{DEMO[role].username}</code>
                      </div>
                      <div>
                        <span className="text-slate-500">Pass </span>
                        <code className="text-slate-300 font-mono">{DEMO[role].password}</code>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
