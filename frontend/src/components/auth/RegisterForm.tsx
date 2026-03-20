import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
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
  const { register: reg, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { role: 'guest' } });
  const registerMutation = useRegister();

  return (
    <form onSubmit={handleSubmit((data) => registerMutation.mutate(data))} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Input label="First Name" {...reg('first_name')} error={errors.first_name?.message} />
        <Input label="Last Name" {...reg('last_name')} error={errors.last_name?.message} />
      </div>
      <Input label="Email" type="email" {...reg('email')} error={errors.email?.message} />
      <Input label="Password" type="password" {...reg('password')} error={errors.password?.message} />
      <Input label="Phone (optional)" type="tel" {...reg('phone')} />
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">I am a...</label>
        <div className="flex gap-4">
          <label className="flex items-center gap-2"><input type="radio" value="guest" {...reg('role')} className="text-wisestay-500" /> Guest</label>
          <label className="flex items-center gap-2"><input type="radio" value="owner" {...reg('role')} className="text-wisestay-500" /> Property Owner</label>
        </div>
      </div>
      <Button type="submit" className="w-full" loading={registerMutation.isPending}>Create Account</Button>
    </form>
  );
}
