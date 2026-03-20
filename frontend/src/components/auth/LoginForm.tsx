import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useTranslation } from 'react-i18next';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { useLogin } from '@/hooks/useAuth';

const schema = z.object({
  email: z.string().email('Valid email required'),
  password: z.string().min(1, 'Password required'),
});

type FormData = z.infer<typeof schema>;

export function LoginForm() {
  const { t } = useTranslation();
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema)
  });
  const login = useLogin();

  return (
    <form onSubmit={handleSubmit((data) => login.mutate(data))} className="space-y-5">
      <Input
        label={t('auth.login.email')}
        type="email"
        placeholder={t('auth.login.email_placeholder')}
        {...register('email')}
        error={errors.email?.message}
      />
      <Input
        label={t('auth.login.password')}
        type="password"
        placeholder={t('auth.login.password_placeholder')}
        {...register('password')}
        error={errors.password?.message}
      />
      <Button type="submit" className="w-full" loading={login.isPending}>
        {t('auth.login.submit')}
      </Button>
    </form>
  );
}
