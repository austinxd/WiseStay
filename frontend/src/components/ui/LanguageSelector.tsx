import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe, Check, ChevronDown } from 'lucide-react';

const languages = [
  { code: 'en', name: 'English', short: 'EN' },
  { code: 'es', name: 'Espanol', short: 'ES' },
];

export function LanguageSelector() {
  const { i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentLang = languages.find(l => l.code === i18n.language) || languages[0];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLanguageChange = (langCode: string) => {
    i18n.changeLanguage(langCode);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors"
        aria-label="Select language"
      >
        <Globe className="w-4 h-4" />
        <span className="hidden sm:inline">{currentLang.short}</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-36 bg-white rounded-lg shadow-card border border-neutral-100 py-1 z-50">
          {languages.map((lang) => (
            <button
              key={lang.code}
              onClick={() => handleLanguageChange(lang.code)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors
                         ${i18n.language === lang.code
                           ? 'bg-neutral-50 text-neutral-900'
                           : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'}`}
            >
              <span className="flex-1 text-left">{lang.name}</span>
              {i18n.language === lang.code && (
                <Check className="w-4 h-4 text-brand-gold" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
