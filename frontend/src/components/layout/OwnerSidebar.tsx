import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Home, CalendarDays, DollarSign, CreditCard, User } from 'lucide-react';

const links = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/my-properties', icon: Home, label: 'Properties' },
  { to: '/reservations', icon: CalendarDays, label: 'Reservations' },
  { to: '/revenue', icon: DollarSign, label: 'Revenue' },
  { to: '/payouts', icon: CreditCard, label: 'Payouts' },
  { to: '/profile', icon: User, label: 'Profile' },
];

export function OwnerSidebar() {
  return (
    <nav className="w-64 bg-white border-r border-gray-200 min-h-screen hidden lg:block">
      <div className="p-4 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to} to={to}
            className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isActive ? 'bg-wisestay-50 text-wisestay-700' : 'text-gray-600 hover:bg-gray-50'}`}
          >
            <Icon className="w-5 h-5" />{label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
