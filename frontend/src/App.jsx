import { useState, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import HomePage from './components/HomePage';
import LoginView from './components/LoginView';
import SharedHeader from './components/SharedHeader';
import NurseDashboard from './components/NurseDashboard';
import PhysicianDashboard from './components/PhysicianDashboard';
import { initialNotes, initialTasks, labResults as initialLabs } from './mockData';

const API_BASE = 'http://localhost:8000/api';

export default function App() {
  const [view, setView] = useState('home');
  const [notes, setNotes] = useState(initialNotes);
  const [tasks, setTasks] = useState([]);
  const [labs, setLabs] = useState(initialLabs);

  useEffect(() => {
    // Fetch initial tasks from backend
    fetch(`${API_BASE}/tasks`)
      .then(res => res.json())
      .then(data => {
        // If the backend has no data yet, maybe fallback to initialTasks or just set the fetched data
        if (data.length > 0) {
          setTasks(data);
        } else {
          setTasks(initialTasks);
        }
      })
      .catch(err => {
        console.error("Failed to fetch tasks, using mock data", err);
        setTasks(initialTasks);
      });
  }, []);

  const handleLogin = (role) => {
    setView(role);
  };

  const handleLogout = () => {
    setView('home');
  };

  const handleAddNote = (note) => {
    setNotes(prev => [...prev, note]);
  };

  const handleAddTask = async (task) => {
    try {
      const res = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: task.patientId,
          description: task.task,
          scheduled_time: task.time,
          task_type: task.type,
          priority: task.priority
        })
      });
      if (res.ok) {
        const newTask = await res.json();
        // Map backend format to frontend format
        const formattedTask = {
          id: newTask.id,
          patient: task.patient,
          patientId: newTask.patient_id,
          bed: task.bed,
          task: newTask.description,
          time: newTask.scheduled_time,
          type: newTask.task_type,
          priority: newTask.priority,
          done: newTask.is_completed
        };
        setTasks(prev => [...prev, formattedTask]);
      }
    } catch (err) {
      console.error("Error creating task", err);
      // Fallback for demo
      setTasks(prev => [...prev, { ...task, id: Date.now() }]);
    }
  };

  const handleToggleTask = async (id) => {
    const task = tasks.find(t => t.id === id);
    if (!task) return;
    
    try {
      const res = await fetch(`${API_BASE}/tasks/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_completed: !task.done })
      });
      if (res.ok) {
        setTasks(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t));
      }
    } catch (err) {
      console.error("Error toggling task", err);
      // Fallback
      setTasks(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t));
    }
  };

  const handleAddLab = async (labData) => {
    // Optimistically update local state for immediate UI feedback
    setLabs(prev => {
      const pid = labData.patient_id;
      const currentPatientLabs = prev[pid] || [];
      const newLab = {
        test: labData.test_name,
        value: labData.value,
        unit: labData.unit,
        range: labData.reference_range,
        status: labData.status
      };
      
      // Remove any existing lab with the same test name to "update" it
      const filteredLabs = currentPatientLabs.filter(l => {
        const t1 = l.test.toLowerCase().replace('white blood cell count', 'wbc count');
        const t2 = newLab.test.toLowerCase().replace('white blood cell count', 'wbc count');
        return t1 !== t2;
      });
      
      return { ...prev, [pid]: [newLab, ...filteredLabs] };
    });

    try {
      const res = await fetch(`${API_BASE}/labs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(labData)
      });
      if (res.ok) {
        await res.json();
      }
    } catch (err) {
      console.warn("Backend not running - lab result saved locally only", err);
    }
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
          <NurseDashboard key="nurse" notes={notes} onAddNote={handleAddNote} tasks={tasks} onToggleTask={handleToggleTask} onAddLab={handleAddLab} labs={labs} />
        ) : (
          <PhysicianDashboard key="physician" notes={notes} onAddNote={handleAddNote} tasks={tasks} onAddTask={handleAddTask} labs={labs} />
        )}
      </AnimatePresence>
    </div>
  );
}
