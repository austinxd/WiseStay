import { Outlet } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { AppHeader } from './AppHeader';
import { GuestSidebar } from './GuestSidebar';
import { OwnerSidebar } from './OwnerSidebar';

export function AppLayout() {
  const { user } = useAuthStore();
  const Sidebar = user?.role === 'owner' ? OwnerSidebar : GuestSidebar;

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
