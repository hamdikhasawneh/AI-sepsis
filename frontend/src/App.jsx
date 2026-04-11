import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import HomePage from './components/HomePage';
import LoginView from './components/LoginView';
import SharedHeader from './components/SharedHeader';
import NurseDashboard from './components/NurseDashboard';
import PhysicianDashboard from './components/PhysicianDashboard';
import { initialNotes } from './mockData';

export default function App() {
  const [view, setView] = useState('home');
  const [notes, setNotes] = useState(initialNotes);

  const handleLogin = (role) => {
    setView(role);
  };

  const handleLogout = () => {
    setView('home');
  };

  const handleAddNote = (note) => {
    setNotes(prev => [...prev, note]);
  };

  if (view === 'home') {
    return <HomePage onNavigateLogin={() => setView('login')} />;
  }

  if (view === 'login') {
    return <LoginView onLogin={handleLogin} onBack={() => setView('home')} />;
  }

  return (
    <div className="app-shell">
      <SharedHeader role={view} onLogout={handleLogout} />
      <AnimatePresence mode="wait">
        {view === 'nurse' ? (
          <NurseDashboard key="nurse" notes={notes} onAddNote={handleAddNote} />
        ) : (
          <PhysicianDashboard key="physician" notes={notes} onAddNote={handleAddNote} />
        )}
      </AnimatePresence>
    </div>
  );
}
