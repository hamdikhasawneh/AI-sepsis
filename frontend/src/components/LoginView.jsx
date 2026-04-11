import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Stethoscope, HeartPulse, Eye, EyeOff, ArrowLeft, Lock, User } from 'lucide-react';

const CREDENTIALS = {
  physician: { username: 'dr.rivera', password: 'physician123', name: 'Dr. James Rivera' },
  nurse: { username: 'nurse.station', password: 'nurse123', name: 'Nurse Station A' },
};

export default function LoginView({ onLogin, onBack }) {
  const [selectedRole, setSelectedRole] = useState(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!username.trim() || !password.trim()) {
      setError('Please enter both username and password');
      return;
    }

    const cred = CREDENTIALS[selectedRole];
    if (username === cred.username && password === cred.password) {
      setLoading(true);
      setTimeout(() => onLogin(selectedRole), 800);
    } else {
      setError('Invalid credentials. Check the hint below.');
    }
  };

  const handleRoleSelect = (role) => {
    setSelectedRole(role);
    setUsername('');
    setPassword('');
    setError('');
  };

  return (
    <div className="login-view">
      <div className="login-bg-glow" />
      <div className="login-bg-glow login-bg-glow-2" />

      <motion.div
        className="login-panel"
        initial={{ opacity: 0, y: 30, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      >
        {/* Logo */}
        <div className="login-logo">
          <motion.div
            className="login-logo-icon"
            animate={{ scale: [1, 1.08, 1] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          >
            <Activity size={40} />
          </motion.div>
          <h1>SepsisAI</h1>
        </div>

        <AnimatePresence mode="wait">
          {/* ── Step 1: Role Selection ── */}
          {!selectedRole && (
            <motion.div
              key="role-select"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <p className="login-subtitle">
                Select your role to continue
              </p>

              {onBack && (
                <button className="login-back-btn" onClick={onBack}>
                  <ArrowLeft size={15} /> Back to Home
                </button>
              )}

              <div className="login-roles">
                <motion.button
                  className="login-role-btn"
                  onClick={() => handleRoleSelect('physician')}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="login-role-icon physician">
                    <Stethoscope size={24} />
                  </div>
                  <div className="login-role-info">
                    Physician
                    <span>Clinical deep-dive & AI reasoning</span>
                  </div>
                </motion.button>

                <motion.button
                  className="login-role-btn"
                  onClick={() => handleRoleSelect('nurse')}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="login-role-icon nurse">
                    <HeartPulse size={24} />
                  </div>
                  <div className="login-role-info">
                    Nursing Unit
                    <span>Unit monitoring, labs & alert triage</span>
                  </div>
                </motion.button>
              </div>
            </motion.div>
          )}

          {/* ── Step 2: Credential Form ── */}
          {selectedRole && (
            <motion.div
              key="credentials"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <button className="login-back-btn" onClick={() => setSelectedRole(null)}>
                <ArrowLeft size={15} /> Choose different role
              </button>

              <div className="login-role-selected">
                <div className={`login-role-icon-sm ${selectedRole}`}>
                  {selectedRole === 'physician' ? <Stethoscope size={18} /> : <HeartPulse size={18} />}
                </div>
                <span>
                  {selectedRole === 'physician' ? 'Physician Login' : 'Nursing Unit Login'}
                </span>
              </div>

              <form className="login-form" onSubmit={handleSubmit}>
                {error && (
                  <motion.div
                    className="login-error"
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    {error}
                  </motion.div>
                )}

                <div className="login-field">
                  <label htmlFor="username">Username</label>
                  <div className="login-input-wrap">
                    <User size={16} className="login-input-icon" />
                    <input
                      id="username"
                      type="text"
                      placeholder="Enter your username"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      autoFocus
                      autoComplete="username"
                    />
                  </div>
                </div>

                <div className="login-field">
                  <label htmlFor="password">Password</label>
                  <div className="login-input-wrap">
                    <Lock size={16} className="login-input-icon" />
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      className="login-eye-btn"
                      onClick={() => setShowPassword(!showPassword)}
                      tabIndex={-1}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <motion.button
                  type="submit"
                  className="btn btn-primary btn-full login-submit"
                  disabled={loading}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                >
                  {loading ? (
                    <span className="login-spinner" />
                  ) : (
                    'Sign In'
                  )}
                </motion.button>
              </form>

              <div className="login-hint">
                <p className="login-hint-title">Demo Credentials</p>
                <div className="login-hint-cred">
                  <span>Username:</span>
                  <code>{CREDENTIALS[selectedRole].username}</code>
                </div>
                <div className="login-hint-cred">
                  <span>Password:</span>
                  <code>{CREDENTIALS[selectedRole].password}</code>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
