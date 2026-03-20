import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useTranslation } from 'react-i18next';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { useRegister } from '@/hooks/useAuth';

const schema = z.object({
  first_name: z.string().min(1, 'First name required'),
  last_name: z.string().min(1, 'Last name required'),
  email: z.string().email('Valid email required'),
  password: z.string().min(8, 'At least 8 characters'),
  phone: z.string().optional(),
  role: z.enum(['guest', 'owner']),
});

type FormData = z.infer<typeof schema>;

export function RegisterForm() {
  const { t } = useTranslation();
  const { register: reg, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { role: 'guest' }
  });
  const registerMutation = useRegister();

  return (
    <form onSubmit={handleSubmit((data) => registerMutation.mutate(data))} className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <Input
          label={t('auth.register.first_name')}
          {...reg('first_name')}
          error={errors.first_name?.message}
        />
        <Input
          label={t('auth.register.last_name')}
          {...reg('last_name')}
          error={errors.last_name?.message}
        />
      </div>
      <Input
        label={t('auth.register.email')}
        type="email"
        {...reg('email')}
        error={errors.email?.message}
      />
      <Input
        label={t('auth.register.password')}
        type="password"
        {...reg('password')}
        error={errors.password?.message}
      />
      <Input
        label={t('auth.register.phone')}
        type="tel"
        {...reg('phone')}
      />

      <div>
        <label className="input-label mb-3 block">{t('auth.register.role')}</label>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              value="guest"
              {...reg('role')}
              className="w-4 h-4 text-brand-gold border-neutral-300 focus:ring-brand-gold"
            />
            <span className="text-neutral-700 text-sm">{t('auth.register.role_guest')}</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              value="owner"
              {...reg('role')}
              className="w-4 h-4 text-brand-gold border-neutral-300 focus:ring-brand-gold"
            />
            <span className="text-neutral-700 text-sm">{t('auth.register.role_owner')}</span>
          </label>
        </div>
      </div>

      <Button type="submit" className="w-full" loading={registerMutation.isPending}>
        {t('auth.register.submit')}
      </Button>
    </form>
  );
}
