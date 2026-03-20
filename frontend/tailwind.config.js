/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f8f6f3',
          100: '#f0ece5',
          200: '#e2d9cc',
          300: '#cdbea8',
          400: '#b49d7e',
          500: '#a08563',
          600: '#8c7050',
          700: '#745c43',
          800: '#614d3a',
          900: '#524233',
        },
        navy: {
          50: '#f3f5f9',
          100: '#e4e9f2',
          200: '#cfd7e8',
          300: '#aebdd7',
          400: '#879bc2',
          500: '#6a7fb0',
          600: '#5668a0',
          700: '#4a5890',
          800: '#1e293b',
          900: '#0f172a',
          950: '#080d19',
        },
        accent: {
          50: '#fefce8',
          100: '#fef9c3',
          200: '#fef08a',
          300: '#fde047',
          400: '#facc15',
          500: '#d4a012',
          600: '#b8860b',
          700: '#92690a',
          800: '#784f0b',
          900: '#65420e',
        },
        success: { 500: '#10b981', 50: '#ecfdf5' },
        danger: { 500: '#ef4444', 50: '#fef2f2' },
      },
      fontFamily: {
        sans: ['"DM Sans"', 'Inter', 'system-ui', 'sans-serif'],
        heading: ['"Playfair Display"', 'Georgia', 'serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'elevated': '0 10px 40px -10px rgba(0, 0, 0, 0.12)',
        'glow': '0 0 40px rgba(212, 160, 18, 0.15)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp: { '0%': { opacity: '0', transform: 'translateY(20px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        float: { '0%, 100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-10px)' } },
      },
    },
  },
  plugins: [],
};
