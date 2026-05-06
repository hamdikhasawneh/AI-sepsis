import { useState, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import HomePage from './components/HomePage';
import LoginView from './components/LoginView';
import SharedHeader from './components/SharedHeader';
import NurseDashboard from './components/NurseDashboard';
import PhysicianDashboard from './components/PhysicianDashboard';
import { initialNotes, initialTasks, labResults as initialLabs, initialAlerts } from './mockData';

const API_BASE = 'http://localhost:8000/api';
const WS_URL = 'ws://localhost:8000/ws/alerts';

export default function App() {
  const [view, setView] = useState('home');
  const [notes, setNotes] = useState(initialNotes);
  const [tasks, setTasks] = useState([]);
  const [labs, setLabs] = useState(initialLabs);
  const [alerts, setAlerts] = useState(initialAlerts);

  // Helper for authenticated fetch
  const authFetch = async (url, options = {}) => {
    const token = localStorage.getItem('sepsis_token');
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
    return fetch(url, { ...options, headers });
  };

  // ─── WebSocket for Real-time Alerts ───
  useEffect(() => {
    let socket;
    let reconnectTimeout;

    const connect = () => {
      socket = new WebSocket(WS_URL);

      socket.onopen = () => {
        console.log('✅ Connected to Sepsis Alert WebSocket');
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'NEW_ALERT') {
            console.log('🚨 NEW SEPSIS ALERT RECEIVED:', data.alert);
            
            const newAlert = {
              id: data.alert.alert_id,
              patientId: data.alert.patient_id,
              patientName: data.alert.patient_name,
              title: data.alert.alert_level === 'critical' ? 'CRITICAL SEPSIS RISK' : 'HIGH SEPSIS RISK',
              message: data.alert.alert_message,
              level: data.alert.alert_level,
              timestamp: data.alert.created_at
            };

            setAlerts(prev => [newAlert, ...prev]);
            
            if (Notification.permission === 'granted') {
              new Notification(newAlert.title, { body: newAlert.message });
            }
          }
        } catch (err) {
          console.error('Error parsing WebSocket message', err);
        }
      };

      socket.onclose = () => {
        console.warn('⚠️ WebSocket disconnected. Reconnecting in 5s...');
        reconnectTimeout = setTimeout(connect, 5000);
      };

      socket.onerror = (err) => {
        console.error('❌ WebSocket error:', err);
        socket.close();
      };
    };

    connect();
    
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }

    return () => {
      if (socket) socket.close();
      clearTimeout(reconnectTimeout);
    };
  }, []);

  useEffect(() => {
    if (view === 'home' || view === 'login') return;

    // Fetch initial tasks from backend using authFetch
    authFetch(`${API_BASE}/tasks`)
      .then(res => res.json())
      .then(data => {
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
  }, [view]);

  const handleLogin = (role) => {
    setView(role);
  };

  const handleLogout = () => {
    localStorage.removeItem('sepsis_token');
    setView('home');
  };

  const handleAddNote = (note) => {
    setNotes(prev => [...prev, note]);
  };

  const handleAddTask = async (task) => {
    try {
      const res = await authFetch(`${API_BASE}/tasks`, {
        method: 'POST',
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
      setTasks(prev => [...prev, { ...task, id: Date.now() }]);
    }
  };

  const handleToggleTask = async (id) => {
    const task = tasks.find(t => t.id === id);
    if (!task) return;
    
    try {
      const res = await authFetch(`${API_BASE}/tasks/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_completed: !task.done })
      });
      if (res.ok) {
        setTasks(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t));
      }
    } catch (err) {
      console.error("Error toggling task", err);
      setTasks(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t));
    }
  };

  const handleAddLab = async (labData) => {
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
      
      const filteredLabs = currentPatientLabs.filter(l => {
        const t1 = l.test.toLowerCase().replace('white blood cell count', 'wbc count');
        const t2 = newLab.test.toLowerCase().replace('white blood cell count', 'wbc count');
        return t1 !== t2;
      });
      
      return { ...prev, [pid]: [newLab, ...filteredLabs] };
    });

    try {
      const res = await authFetch(`${API_BASE}/labs`, {
        method: 'POST',
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
          <NurseDashboard 
            key="nurse" 
            notes={notes} 
            onAddNote={handleAddNote} 
            tasks={tasks} 
            onToggleTask={handleToggleTask} 
            onAddLab={handleAddLab} 
            labs={labs} 
          />
        ) : (
          <PhysicianDashboard 
            key="physician" 
            notes={notes} 
            onAddNote={handleAddNote} 
            tasks={tasks} 
            onAddTask={handleAddTask} 
            labs={labs} 
            alerts={alerts} 
            setAlerts={setAlerts}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
