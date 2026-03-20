import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { useLogin } from '@/hooks/useAuth';

const schema = z.object({
  email: z.string().email('Valid email required'),
  password: z.string().min(1, 'Password required'),
});

type FormData = z.infer<typeof schema>;

export function LoginForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema) });
  const login = useLogin();

  return (
    <form onSubmit={handleSubmit((data) => login.mutate(data))} className="space-y-4">
      <Input label="Email" type="email" {...register('email')} error={errors.email?.message} />
      <Input label="Password" type="password" {...register('password')} error={errors.password?.message} />
      <Button type="submit" className="w-full" loading={login.isPending}>Log in</Button>
    </form>
  );
}
