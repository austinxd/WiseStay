import { Link } from 'react-router-dom';
import { Menu, LogOut, Sparkles, Bell } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { useLogout } from '@/hooks/useAuth';
import { useUIStore } from '@/stores/uiStore';

export function AppHeader() {
  const { user } = useAuthStore();
  const logout = useLogout();
  const { toggleMobileMenu } = useUIStore();

  return (
    <header className="bg-white/80 backdrop-blur-xl border-b border-gray-100 sticky top-0 z-40">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-4">
            <button className="lg:hidden p-2 rounded-xl hover:bg-gray-50 text-gray-500" onClick={toggleMobileMenu}>
              <Menu className="w-5 h-5" />
            </button>
            <Link to="/dashboard" className="flex items-center gap-2">
              <div className="w-7 h-7 bg-accent-500 rounded-lg flex items-center justify-center"><Sparkles className="w-3.5 h-3.5 text-white" /></div>
              <span className="text-lg font-heading font-bold text-navy-900">WiseStay</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <button className="p-2 rounded-xl hover:bg-gray-50 text-gray-400"><Bell className="w-5 h-5" /></button>
            <div className="flex items-center gap-3 ml-2 pl-4 border-l border-gray-100">
              <div className="w-8 h-8 rounded-full bg-navy-900 text-white flex items-center justify-center text-sm font-semibold">{user?.first_name?.[0] || '?'}</div>
              <span className="text-sm font-medium text-navy-700 hidden sm:block">{user?.first_name}</span>
            </div>
            <button onClick={logout} className="p-2 rounded-xl hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors" title="Log out">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
