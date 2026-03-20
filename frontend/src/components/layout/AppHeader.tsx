import { Link } from 'react-router-dom';
import { Menu, LogOut } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { useLogout } from '@/hooks/useAuth';
import { useUIStore } from '@/stores/uiStore';

export function AppHeader() {
  const { user } = useAuthStore();
  const logout = useLogout();
  const { toggleMobileMenu } = useUIStore();

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-4">
            <button className="lg:hidden p-2 rounded-lg hover:bg-gray-100" onClick={toggleMobileMenu}>
              <Menu className="w-5 h-5" />
            </button>
            <Link to="/dashboard" className="text-xl font-heading font-bold text-wisestay-600">WiseStay</Link>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600 hidden sm:block">{user?.first_name || user?.email}</span>
            <button onClick={logout} className="p-2 rounded-lg hover:bg-gray-100 text-gray-500" title="Log out">
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
