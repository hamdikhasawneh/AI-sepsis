import { useState, useEffect } from 'react';
import { Play, Square, RefreshCcw, Activity } from 'lucide-react';
import { Card, CardBody } from './ui/Card';
import { Button } from './ui/Button';
import { authFetch } from '../store/appStore';

const API_BASE = 'http://localhost:8000/api';

export function SimulationControl() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState('');
  const [status, setStatus] = useState({ running: false, current_case: null, current_hour: 0 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchCases();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  const fetchCases = async () => {
    try {
      const res = await authFetch(`${API_BASE}/simulation/cases`);
      if (res.ok) {
        const data = await res.json();
        setCases(data.cases);
        if (data.cases.length > 0) setSelectedCase(data.cases[0]);
      }
    } catch (err) {
      console.error('Failed to fetch cases', err);
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await authFetch(`${API_BASE}/simulation/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch status', err);
    }
  };

  const handleStart = async () => {
    if (!selectedCase) return;
    setLoading(true);
    try {
      await authFetch(`${API_BASE}/simulation/start?case_name=${selectedCase}`, { method: 'POST' });
      await fetchStatus();
      useAppStore.getState().fetchAll(); // Refresh patient list
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await authFetch(`${API_BASE}/simulation/stop`, { method: 'POST' });
      await fetchStatus();
      useAppStore.getState().fetchAll(); // Refresh patient list
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 w-80">
      <Card className="shadow-2xl border-indigo-500/30 bg-slate-900/90 backdrop-blur-md">
        <CardBody className="p-4">
          <div className="flex items-center gap-2 mb-4 border-b border-slate-700 pb-2">
            <Activity className="w-5 h-5 text-indigo-400" />
            <h3 className="font-bold text-slate-100 uppercase tracking-wider text-sm">Simulation Lab</h3>
          </div>

          {!status.running ? (
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Select Clinical Case</label>
                <select 
                  className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-sm text-slate-200"
                  value={selectedCase}
                  onChange={(e) => setSelectedCase(e.target.value)}
                >
                  {cases.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <Button 
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center gap-2"
                onClick={handleStart}
                disabled={loading || !selectedCase}
              >
                <Play className="w-4 h-4 fill-current" />
                Start Simulation
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-3 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-indigo-300 font-medium">RUNNING: {status.current_case}</span>
                  <span className="animate-pulse flex h-2 w-2 rounded-full bg-indigo-400"></span>
                </div>
                <div className="text-xl font-bold text-slate-100">
                  Hour {status.current_hour} <span className="text-xs font-normal text-slate-400">/ 24</span>
                </div>
                <div className="w-full bg-slate-700 h-1 mt-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-indigo-500 h-full transition-all duration-1000" 
                    style={{ width: `${(status.current_hour / 24) * 100}%` }}
                  ></div>
                </div>
              </div>
              <Button 
                variant="danger"
                className="w-full flex items-center justify-center gap-2"
                onClick={handleStop}
                disabled={loading}
              >
                <Square className="w-4 h-4 fill-current" />
                Stop Simulation
              </Button>
            </div>
          )}
          
          <div className="mt-4 pt-2 border-t border-slate-800 text-[10px] text-slate-500 flex justify-between">
            <span>DST Real-time Replay</span>
            <span>Speed: 1h / 3s</span>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
