import { Navigate } from 'react-router-dom';
import { useAppStore } from '../../store/appStore';

export function ProtectedRoute({ role: requiredRole, children }) {
  const token = useAppStore(s => s.token);
  const user  = useAppStore(s => s.user);

  if (!token) return <Navigate to="/login" replace />;

  if (requiredRole) {
    const userRole = user?.role === 'nurse' ? 'nurse' : 'physician';
    if (userRole !== requiredRole) {
      return <Navigate to={userRole === 'nurse' ? '/nurse' : '/physician'} replace />;
    }
  }

  return children;
}
