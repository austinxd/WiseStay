import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { useState } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/Button';

export function Header() {
  const { isAuthenticated } = useAuthStore();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl font-heading font-bold text-wisestay-600">WiseStay</span>
          </Link>

          <nav className="hidden md:flex items-center gap-6">
            <Link to="/properties" className="text-sm font-medium text-gray-600 hover:text-wisestay-600">Properties</Link>
            <Link to="/loyalty-program" className="text-sm font-medium text-gray-600 hover:text-wisestay-600">Rewards</Link>
            {isAuthenticated ? (
              <Link to="/dashboard"><Button size="sm">Dashboard</Button></Link>
            ) : (
              <div className="flex items-center gap-3">
                <Link to="/login"><Button variant="ghost" size="sm">Log in</Button></Link>
                <Link to="/register"><Button size="sm">Sign up</Button></Link>
              </div>
            )}
          </nav>

          <button className="md:hidden p-2" onClick={() => setMenuOpen(!menuOpen)}>
            {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {menuOpen && (
          <div className="md:hidden py-4 border-t space-y-3">
            <Link to="/properties" className="block text-sm font-medium text-gray-600 py-2" onClick={() => setMenuOpen(false)}>Properties</Link>
            <Link to="/loyalty-program" className="block text-sm font-medium text-gray-600 py-2" onClick={() => setMenuOpen(false)}>Rewards</Link>
            {isAuthenticated ? (
              <Link to="/dashboard" onClick={() => setMenuOpen(false)}><Button className="w-full">Dashboard</Button></Link>
            ) : (
              <div className="space-y-2">
                <Link to="/login" onClick={() => setMenuOpen(false)}><Button variant="outline" className="w-full">Log in</Button></Link>
                <Link to="/register" onClick={() => setMenuOpen(false)}><Button className="w-full">Sign up</Button></Link>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
