import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { RegisterForm } from '@/components/auth/RegisterForm';

export function RegisterPage() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-neutral-50 flex items-center justify-center py-16">
      <div className="w-full max-w-md px-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-display font-bold text-neutral-900 mb-2">
            {t('auth.register.title')}
          </h1>
          <p className="text-neutral-500">
            {t('auth.register.subtitle')}
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-card p-8">
          <RegisterForm />
        </div>

        <p className="text-center text-sm text-neutral-500 mt-6">
          {t('auth.register.have_account')}{' '}
          <Link to="/login" className="text-brand-gold hover:underline font-medium">
            {t('auth.register.login_link')}
          </Link>
        </p>
      </div>
    </div>
  );
}
