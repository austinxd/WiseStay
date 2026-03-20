import api from '@/config/api';
import type { AuthTokens, LoginRequest, RegisterRequest, UserProfile } from '@/types/auth';

export const authService = {
  login: (data: LoginRequest) => api.post<AuthTokens>('/accounts/token/', data).then(r => r.data),
  register: (data: RegisterRequest) => api.post('/accounts/register/', data).then(r => r.data),
  getMe: () => api.get<UserProfile>('/accounts/me/').then(r => r.data),
  refreshToken: (refresh: string) => api.post<{ access: string }>('/accounts/token/refresh/', { refresh }).then(r => r.data),
};
