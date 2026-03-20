/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        wisestay: {
          50: '#f0f7ff',
          100: '#e0efff',
          200: '#b8dbff',
          300: '#7ac0ff',
          400: '#36a3ff',
          500: '#0284c7',
          600: '#0369a1',
          700: '#075985',
          800: '#0c4a6e',
          900: '#0a3049',
        },
        accent: {
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        heading: ['Sora', 'Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
