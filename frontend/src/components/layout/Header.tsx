import { Link } from 'react-router-dom';
import { Menu, X, Phone } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { LanguageSelector } from '@/components/ui/LanguageSelector';

export function Header() {
  const { t } = useTranslation();
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
    <header className="sticky top-0 z-50 bg-white border-b border-neutral-100">
      <div className="container-page">
        <div className="flex items-center justify-between h-16 lg:h-20">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl font-display font-bold text-neutral-900">
              Wise<span className="text-brand-gold">Stay</span>
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-8">
            <Link
              to="/properties"
              className="text-neutral-600 hover:text-neutral-900 font-medium transition-colors"
            >
              {t('nav.properties')}
            </Link>
            <Link
              to="/how-it-works"
              className="text-neutral-600 hover:text-neutral-900 font-medium transition-colors"
            >
              {t('nav.how_it_works')}
            </Link>
            <Link
              to="/for-owners"
              className="text-neutral-600 hover:text-neutral-900 font-medium transition-colors"
            >
              {t('nav.for_owners')}
            </Link>
          </nav>

          {/* Right side */}
          <div className="hidden lg:flex items-center gap-4">
            {/* Contact */}
            <a
              href="tel:+13055551234"
              className="flex items-center gap-2 text-neutral-600 hover:text-neutral-900 transition-colors"
            >
              <Phone className="w-4 h-4" />
              <span className="font-medium">+1 (305) 555-1234</span>
            </a>

            <div className="w-px h-6 bg-neutral-200" />

            <LanguageSelector />

            {isAuthenticated ? (
              <Link to="/dashboard" className="btn-primary">
                {t('nav.dashboard')}
              </Link>
            ) : (
              <div className="flex items-center gap-3">
                <Link
                  to="/login"
                  className="text-neutral-600 hover:text-neutral-900 font-medium transition-colors"
                >
                  {t('nav.login')}
                </Link>
                <Link to="/register" className="btn-primary">
                  {t('nav.register')}
                </Link>
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="flex lg:hidden items-center gap-3">
            <LanguageSelector />
            <button
              className="p-2 text-neutral-600 hover:text-neutral-900"
              onClick={() => setMenuOpen(!menuOpen)}
            >
              {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="lg:hidden py-4 border-t border-neutral-100">
            <nav className="space-y-1">
              <Link
                to="/properties"
                className="block px-4 py-3 text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50 rounded-lg font-medium"
                onClick={() => setMenuOpen(false)}
              >
                {t('nav.properties')}
              </Link>
              <Link
                to="/how-it-works"
                className="block px-4 py-3 text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50 rounded-lg font-medium"
                onClick={() => setMenuOpen(false)}
              >
                {t('nav.how_it_works')}
              </Link>
              <Link
                to="/for-owners"
                className="block px-4 py-3 text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50 rounded-lg font-medium"
                onClick={() => setMenuOpen(false)}
              >
                {t('nav.for_owners')}
              </Link>
            </nav>

            <div className="h-px bg-neutral-100 my-4" />

            <div className="px-4 space-y-3">
              {isAuthenticated ? (
                <Link
                  to="/dashboard"
                  onClick={() => setMenuOpen(false)}
                  className="btn-primary w-full justify-center"
                >
                  {t('nav.dashboard')}
                </Link>
              ) : (
                <>
                  <Link
                    to="/login"
                    onClick={() => setMenuOpen(false)}
                    className="btn-secondary w-full justify-center"
                  >
                    {t('nav.login')}
                  </Link>
                  <Link
                    to="/register"
                    onClick={() => setMenuOpen(false)}
                    className="btn-primary w-full justify-center"
                  >
                    {t('nav.register')}
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
