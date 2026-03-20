import { Link } from 'react-router-dom';
import { RegisterForm } from '@/components/auth/RegisterForm';

export function RegisterPage() {
  return (
    <div className="container-page py-16">
      <div className="max-w-md mx-auto">
        <h1 className="text-2xl font-heading font-bold text-center mb-8">Create Your Account</h1>
        <RegisterForm />
        <p className="text-center text-sm text-gray-500 mt-4">Already have an account? <Link to="/login" className="text-wisestay-600 hover:underline">Log in</Link></p>
      </div>
    </div>
  );
}
