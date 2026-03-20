import { ButtonHTMLAttributes, forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'gold';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

const variants = {
  primary: 'bg-neutral-900 text-white hover:bg-neutral-800',
  secondary: 'bg-white text-neutral-900 border border-neutral-300 hover:bg-neutral-50 hover:border-neutral-400',
  outline: 'bg-white text-neutral-900 border border-neutral-300 hover:bg-neutral-50 hover:border-neutral-400',
  ghost: 'bg-transparent text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  gold: 'bg-brand-gold text-white hover:bg-opacity-90',
};

const sizes = {
  sm: 'px-4 py-2 text-sm',
  md: 'px-6 py-3 text-sm',
  lg: 'px-8 py-4 text-base',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, children, disabled, className = '', ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={`
        inline-flex items-center justify-center font-medium rounded-lg
        transition-colors duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]}
        ${sizes[size]}
        ${className}
      `}
      {...props}
    >
      {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
      {children}
    </button>
  )
);
Button.displayName = 'Button';
