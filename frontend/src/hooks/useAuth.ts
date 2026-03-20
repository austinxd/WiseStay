import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { authService } from '@/services/authService';
import { useAuthStore } from '@/stores/authStore';
import type { LoginRequest, RegisterRequest } from '@/types/auth';

export function useLogin() {
  const { login } = useAuthStore();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: async (data: LoginRequest) => {
      const tokens = await authService.login(data);
      const profile = await authService.getMe();
      return { tokens, profile };
    },
    onSuccess: ({ tokens, profile }) => {
      login(tokens.access, tokens.refresh, profile as any);
      toast.success('Welcome back!');
      navigate('/dashboard');
    },
    onError: () => toast.error('Invalid email or password'),
  });
}

export function useRegister() {
  const navigate = useNavigate();
  return useMutation({
    mutationFn: (data: RegisterRequest) => authService.register(data),
    onSuccess: () => { toast.success('Account created! Please log in.'); navigate('/login'); },
    onError: (err: any) => toast.error(err.response?.data?.error || 'Registration failed'),
  });
}

export function useLogout() {
  const { logout } = useAuthStore();
  const navigate = useNavigate();
  return () => { logout(); navigate('/'); toast.success('Logged out'); };
}
