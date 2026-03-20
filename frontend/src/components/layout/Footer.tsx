import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Phone, Mail, MapPin } from 'lucide-react';

export function Footer() {
  const { t } = useTranslation();
  const year = new Date().getFullYear();

  return (
    <footer className="bg-neutral-900 text-white">
      <div className="container-page py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12">
          {/* Brand */}
          <div>
            <Link to="/" className="inline-block mb-4">
              <span className="text-2xl font-display font-bold">
                Wise<span className="text-brand-gold">Stay</span>
              </span>
            </Link>
            <p className="text-neutral-400 text-sm leading-relaxed mb-6">
              {t('footer.tagline')}
            </p>
            <div className="space-y-3">
              <a href="tel:+13055551234" className="flex items-center gap-3 text-neutral-400 hover:text-white transition-colors">
                <Phone className="w-4 h-4" />
                <span className="text-sm">+1 (305) 555-1234</span>
              </a>
              <a href="mailto:hello@wisestay.io" className="flex items-center gap-3 text-neutral-400 hover:text-white transition-colors">
                <Mail className="w-4 h-4" />
                <span className="text-sm">hello@wisestay.io</span>
              </a>
              <div className="flex items-center gap-3 text-neutral-400">
                <MapPin className="w-4 h-4" />
                <span className="text-sm">Miami, Florida</span>
              </div>
            </div>
          </div>

          {/* For Guests */}
          <div>
            <h4 className="font-semibold text-white mb-4">{t('footer.for_guests')}</h4>
            <ul className="space-y-3">
              <li>
                <Link to="/properties" className="text-neutral-400 hover:text-white text-sm transition-colors">
                  {t('footer.browse_properties')}
                </Link>
              </li>
              <li>
                <Link to="/how-it-works" className="text-neutral-400 hover:text-white text-sm transition-colors">
                  {t('footer.how_it_works')}
                </Link>
              </li>
            </ul>
          </div>

          {/* For Owners */}
          <div>
            <h4 className="font-semibold text-white mb-4">{t('footer.for_owners')}</h4>
            <ul className="space-y-3">
              <li>
                <Link to="/register" className="text-neutral-400 hover:text-white text-sm transition-colors">
                  {t('footer.list_property')}
                </Link>
              </li>
              <li>
                <Link to="/login" className="text-neutral-400 hover:text-white text-sm transition-colors">
                  {t('footer.owner_dashboard')}
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="font-semibold text-white mb-4">{t('footer.legal')}</h4>
            <ul className="space-y-3">
              <li>
                <a href="#" className="text-neutral-400 hover:text-white text-sm transition-colors">
                  {t('footer.privacy')}
                </a>
              </li>
              <li>
                <a href="#" className="text-neutral-400 hover:text-white text-sm transition-colors">
                  {t('footer.terms')}
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-neutral-800 mt-12 pt-8">
          <p className="text-neutral-500 text-sm text-center">
            {t('footer.copyright', { year })}
          </p>
        </div>
      </div>
    </footer>
  );
}
