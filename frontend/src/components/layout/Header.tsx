import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Sparkles } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/Button';

export function Header() {
  const { isAuthenticated } = useAuthStore();
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();
  const isHome = location.pathname === '/';

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const headerBg = isHome && !scrolled
    ? 'bg-transparent'
    : 'bg-white/80 backdrop-blur-xl border-b border-gray-100 shadow-sm';
  const textColor = isHome && !scrolled ? 'text-white' : 'text-navy-800';
  const logoColor = isHome && !scrolled ? 'text-white' : 'text-navy-900';

  return (
    <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${headerBg}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-accent-500 rounded-lg flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className={`text-xl font-heading font-bold tracking-tight ${logoColor}`}>WiseStay</span>
          </Link>

          <nav className="hidden md:flex items-center gap-8">
            <Link to="/properties" className={`text-sm font-medium transition-colors hover:text-accent-500 ${textColor}`}>Properties</Link>
            <Link to="/loyalty-program" className={`text-sm font-medium transition-colors hover:text-accent-500 ${textColor}`}>Rewards</Link>
            {isAuthenticated ? (
              <Link to="/dashboard"><Button size="sm">Dashboard</Button></Link>
            ) : (
              <div className="flex items-center gap-3">
                <Link to="/login"><Button variant="ghost" size="sm" className={isHome && !scrolled ? 'text-white hover:bg-white/10' : ''}>Log in</Button></Link>
                <Link to="/register"><Button size="sm">Get Started</Button></Link>
              </div>
            )}
          </nav>

          <button className={`md:hidden p-2 rounded-xl ${textColor}`} onClick={() => setMenuOpen(!menuOpen)}>
            {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {menuOpen && (
          <div className="md:hidden py-6 border-t border-gray-100 bg-white rounded-b-2xl animate-fade-in">
            <div className="space-y-1">
              <Link to="/properties" className="block px-4 py-3 text-sm font-medium text-navy-700 hover:bg-navy-50 rounded-xl" onClick={() => setMenuOpen(false)}>Properties</Link>
              <Link to="/loyalty-program" className="block px-4 py-3 text-sm font-medium text-navy-700 hover:bg-navy-50 rounded-xl" onClick={() => setMenuOpen(false)}>Rewards</Link>
            </div>
            <div className="mt-4 px-4 space-y-2">
              {isAuthenticated ? (
                <Link to="/dashboard" onClick={() => setMenuOpen(false)}><Button className="w-full">Dashboard</Button></Link>
              ) : (
                <>
                  <Link to="/login" onClick={() => setMenuOpen(false)}><Button variant="outline" className="w-full">Log in</Button></Link>
                  <Link to="/register" onClick={() => setMenuOpen(false)}><Button className="w-full">Get Started</Button></Link>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
