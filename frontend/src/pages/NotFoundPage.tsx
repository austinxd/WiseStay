import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';

export function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-heading font-bold text-gray-200 mb-4">404</h1>
        <p className="text-xl text-gray-600 mb-6">Page not found</p>
        <Link to="/"><Button>Go Home</Button></Link>
      </div>
    </div>
  );
}
