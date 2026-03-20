import { ButtonHTMLAttributes, forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
}

const variants = {
  primary: 'bg-navy-900 text-white hover:bg-navy-800 focus:ring-navy-300 shadow-sm hover:shadow-md',
  secondary: 'bg-accent-500 text-white hover:bg-accent-600 focus:ring-accent-300 shadow-sm hover:shadow-md',
  outline: 'border-2 border-navy-200 text-navy-800 hover:border-navy-900 hover:bg-navy-50 focus:ring-navy-200',
  ghost: 'text-navy-600 hover:bg-navy-50 hover:text-navy-900 focus:ring-navy-100',
  danger: 'bg-danger-500 text-white hover:bg-red-600 focus:ring-red-300',
};

const sizes = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-5 py-2.5 text-sm',
  lg: 'px-7 py-3 text-base',
  xl: 'px-8 py-4 text-base',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, children, disabled, className = '', ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-semibold rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
      {children}
    </button>
  )
);
Button.displayName = 'Button';
