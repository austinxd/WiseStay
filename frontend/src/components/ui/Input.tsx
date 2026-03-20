import { InputHTMLAttributes, forwardRef } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...props }, ref) => (
    <div className="w-full">
      {label && (
        <label className="input-label">{label}</label>
      )}
      <input
        ref={ref}
        className={`input ${error ? 'border-red-300 focus:border-red-500 focus:ring-red-500/10' : ''} ${className}`}
        {...props}
      />
      {error && <p className="mt-1.5 text-sm text-red-600">{error}</p>}
    </div>
  )
);
Input.displayName = 'Input';
