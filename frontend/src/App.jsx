import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import ProtectedRoute from './routes/ProtectedRoute';
import Navbar from './components/Navbar';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import PatientsListPage from './pages/PatientsListPage';
import PatientDetailPage from './pages/PatientDetailPage';
import AddPatientPage from './pages/AddPatientPage';
import HistoryPage from './pages/HistoryPage';
import AddVitalsPage from './pages/AddVitalsPage';
import AdminUsersPage from './pages/AdminUsersPage';
import AlertsPage from './pages/AlertsPage';
import AdminSettingsPage from './pages/AdminSettingsPage';

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="loading-screen">Loading...</div>;
  }

  return (
    <div className="app">
      <Navbar />
      <main className={user ? 'main-content' : ''}>
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <LoginPage />} />

          <Route path="/dashboard" element={
            <ProtectedRoute><DashboardPage /></ProtectedRoute>
          } />

          <Route path="/patients" element={
            <ProtectedRoute><PatientsListPage /></ProtectedRoute>
          } />

          <Route path="/patients/add" element={
            <ProtectedRoute allowedRoles={['admin', 'nurse']}><AddPatientPage /></ProtectedRoute>
          } />

          <Route path="/patients/:id" element={
            <ProtectedRoute><PatientDetailPage /></ProtectedRoute>
          } />

          <Route path="/history" element={
            <ProtectedRoute><HistoryPage /></ProtectedRoute>
          } />

          <Route path="/vitals/add" element={
            <ProtectedRoute allowedRoles={['admin', 'nurse']}><AddVitalsPage /></ProtectedRoute>
          } />

          <Route path="/alerts" element={
            <ProtectedRoute><AlertsPage /></ProtectedRoute>
          } />

          <Route path="/admin/users" element={
            <ProtectedRoute allowedRoles={['admin']}><AdminUsersPage /></ProtectedRoute>
          } />

          <Route path="/admin/settings" element={
            <ProtectedRoute allowedRoles={['admin']}><AdminSettingsPage /></ProtectedRoute>
          } />

          <Route path="/" element={<Navigate to={user ? "/dashboard" : "/login"} />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}
