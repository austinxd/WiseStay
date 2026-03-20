import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import type { ReactNode } from 'react';

export function RoleGuard({ role, children }: { role: 'guest' | 'owner'; children: ReactNode }) {
  const { user } = useAuthStore();
  if (user?.role !== role) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
