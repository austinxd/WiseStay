import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Plane, Trophy, MessageCircle, User, Sparkles } from 'lucide-react';

const links = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/trips', icon: Plane, label: 'My Trips' },
  { to: '/loyalty', icon: Trophy, label: 'Rewards' },
  { to: '/chat', icon: MessageCircle, label: 'Concierge' },
  { to: '/profile', icon: User, label: 'Profile' },
];

export function GuestSidebar() {
  return (
    <nav className="w-64 bg-white border-r border-gray-100 min-h-screen hidden lg:block">
      <div className="p-6 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to} to={to}
            className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${isActive ? 'bg-navy-900 text-white shadow-sm' : 'text-gray-500 hover:text-navy-800 hover:bg-gray-50'}`}
          >
            <Icon className="w-[18px] h-[18px]" />{label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
