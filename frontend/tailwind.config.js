/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    fontFamily: {
      sans: ['Open Sans', 'sans-serif'],
    },
    extend: {
      colors: {
        primary: '#fff',
        'primary-color': '#0b0c10',
        brand: '#74d6fd',
        pink: '#e01dee',
        secondary: '#e7ecf0',
        'secondary-color': '#1a1c24',
        'collateral-color': '#1d9259',
        'borrow-color': '#f42222',
        'success-color': '#4caf50',
        'error-color': '#ff5a5f',
        gray: '#83919f',
        'dark-purple': '#120721',
        'light-blue': '#74d5fd',
        'status-opened': '#1edc9e',
        'status-closed': '#433b5a',
        'status-pending': '#83919f',
        'slider-gray': '#393942',
        'dark-gray': '#393942',
        'stormy-gray': '#83919f',
        'deep-purple': '#300734',
        'text-gray': '#798795',
        'warning-colour': '#bdc000',
      },
      fontFamily: {
        primary: ['Open Sans', 'sans-serif'],
        text: ['Rethink Sans', 'sans-serif'],
        stencil: ['Allerta Stencil', 'sans-serif'],
        inter: ['Inter', 'sans-serif'],
      },
      backgroundImage: {
        gradient: 'linear-gradient(73deg, #74d6fd 1.13%, #e01dee 103.45%)',
        'button-gradient': 'linear-gradient(55deg, #74d6fd 0%, #e01dee 100%)',
        'button-gradient-hover': 'linear-gradient(55deg, #74d6fd 0%, #74d6fd 100%)',
        'button-gradient-active': 'linear-gradient(55deg, #58c4ef 0%, #58c4ef 100%)',
        'blue-pink-gradient': 'linear-gradient(90deg, #74d6fd 0%, #e01dee 100%)',
        'blue-pink-gradient-alt': 'linear-gradient(90deg, #49abd2 0%, #e01dee 100%)',
      },
      backgroundPosition: {
        '39p': '39% center',
      },
      boxShadow: {
        custom: '0 4px 12px rgba(0, 0, 0, 0.2)',
      },
    },
  },
  plugins: [],
};
