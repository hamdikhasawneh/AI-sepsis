import { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useAppStore } from './store/appStore';
import HomeScreen      from './screens/HomeScreen';
import LoginScreen     from './screens/LoginScreen';
import PhysicianScreen from './screens/PhysicianScreen';
import NurseScreen     from './screens/NurseScreen';
import { AppHeader }   from './components/shared/AppHeader';
import { PageLoader }  from './components/ui/Spinner';

const WS_URL = 'ws://localhost:8000/ws/alerts';

/* ── Persistent auth check on every protected route ── */
function ProtectedRoute({ role: required, children }) {
  const { token, user, validateSession, fetchAll } = useAppStore();
  const navigate = useNavigate();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!token) { setChecking(false); return; }
    validateSession().then(valid => {
      if (valid) fetchAll();
      setChecking(false);
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (checking) return <PageLoader />;
  if (!token)   return <Navigate to="/login" replace />;

  const role = user?.role === 'nurse' ? 'nurse' : 'physician';
  if (required && role !== required) return <Navigate to={`/${role}`} replace />;

  return children;
}

/* ── WebSocket connector ── */
function WsConnector() {
  const { token, addWsAlert, fetchAll } = useAppStore();
  useEffect(() => {
    if (!token) return;
    let socket, t;
    const connect = () => {
      socket = new WebSocket(WS_URL);
      socket.onmessage = ev => {
        try {
          const d = JSON.parse(ev.data);
          if (d.type === 'NEW_ALERT') {
            const a = d.alert;
            addWsAlert({ id: a.alert_id, patientId: a.patient_id, patientName: a.patient_name || `Patient ${a.patient_id}`, bed: '', title: a.alert_level === 'critical' ? 'CRITICAL SEPSIS RISK' : 'HIGH SEPSIS RISK', message: a.alert_message, level: a.alert_level, timestamp: a.created_at || new Date().toISOString() });
            fetchAll();
          }
        } catch (_) {}
      };
      socket.onclose = () => { t = setTimeout(connect, 5000); };
      socket.onerror = () => socket.close();
    };
    connect();
    
    // Periodic refresh for simulation updates and status
    const poll = setInterval(() => {
      if (document.visibilityState === 'visible') fetchAll();
    }, 5000);

    if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission();
    return () => { 
      if (socket) socket.close(); 
      clearTimeout(t); 
      clearInterval(poll);
    };
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

/* ── Dashboard shell ── */
function Dashboard({ role }) {
  const navigate  = useNavigate();
  const clearAuth = useAppStore(s => s.clearAuth);
  return (
    <div className="min-h-screen bg-void-950 flex flex-col">
      <AppHeader role={role} onLogout={() => { clearAuth(); navigate('/'); }} />
      {role === 'nurse' ? <NurseScreen /> : <PhysicianScreen />}
    </div>
  );
}

/* ── Login route — redirect if already logged in ── */
function LoginRoute() {
  const { token, user } = useAppStore();
  const navigate        = useNavigate();
  if (token) { const r = user?.role === 'nurse' ? 'nurse' : 'physician'; return <Navigate to={`/${r}`} replace />; }
  return <LoginScreen onLogin={role => navigate(`/${role}`, { replace: true })} onBack={() => navigate('/')} />;
}

/* ── Home route — redirect to dashboard if logged in ── */
function HomeRoute() {
  const { token, user } = useAppStore();
  const navigate        = useNavigate();
  if (token) { const r = user?.role === 'nurse' ? 'nurse' : 'physician'; return <Navigate to={`/${r}`} replace />; }
  return <HomeScreen onNavigateLogin={() => navigate('/login')} />;
}

export default function App() {
  return (
    <>
      <WsConnector />
      <Routes>
        <Route path="/"          element={<HomeRoute />} />
        <Route path="/login"     element={<LoginRoute />} />
        <Route path="/physician" element={<ProtectedRoute role="physician"><Dashboard role="physician" /></ProtectedRoute>} />
        <Route path="/nurse"     element={<ProtectedRoute role="nurse"><Dashboard role="nurse" /></ProtectedRoute>} />
        <Route path="*"          element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
