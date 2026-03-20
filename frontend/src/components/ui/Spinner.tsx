import { Loader2 } from 'lucide-react';

export function Spinner({ size = 'md', className = '' }: { size?: 'sm' | 'md' | 'lg'; className?: string }) {
  const s = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' };
  return <Loader2 className={`animate-spin text-wisestay-500 ${s[size]} ${className}`} />;
}

export function PageSpinner() {
  return <div className="flex items-center justify-center min-h-[400px]"><Spinner size="lg" /></div>;
}
