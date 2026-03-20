import { Link } from 'react-router-dom';
import { LoginForm } from '@/components/auth/LoginForm';

export function LoginPage() {
  return (
    <div className="container-page py-16">
      <div className="max-w-md mx-auto">
        <h1 className="text-2xl font-heading font-bold text-center mb-8">Welcome Back</h1>
        <LoginForm />
        <p className="text-center text-sm text-gray-500 mt-4">Don't have an account? <Link to="/register" className="text-wisestay-600 hover:underline">Sign up</Link></p>
      </div>
    </div>
  );
}
