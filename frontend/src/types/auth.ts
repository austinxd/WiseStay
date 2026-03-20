export interface LoginRequest { email: string; password: string }
export interface RegisterRequest { email: string; password: string; first_name: string; last_name: string; phone?: string; role: 'guest' | 'owner' }
export interface AuthTokens { access: string; refresh: string }
export interface UserProfile { id: number; email: string; first_name: string; last_name: string; role: string; phone: string; phone_verified: boolean; email_verified: boolean }
