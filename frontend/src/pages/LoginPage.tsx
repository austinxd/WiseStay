import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LoginForm } from '@/components/auth/LoginForm';

export function LoginPage() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-neutral-50 flex items-center justify-center py-16">
      <div className="w-full max-w-md px-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-display font-bold text-neutral-900 mb-2">
            {t('auth.login.title')}
          </h1>
          <p className="text-neutral-500">
            {t('auth.login.subtitle')}
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-card p-8">
          <LoginForm />
        </div>

        <p className="text-center text-sm text-neutral-500 mt-6">
          {t('auth.login.no_account')}{' '}
          <Link to="/register" className="text-brand-gold hover:underline font-medium">
            {t('auth.login.register_link')}
          </Link>
        </p>
      </div>
    </div>
  );
}
