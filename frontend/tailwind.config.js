/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef6ff',
          100: '#d9ebff',
          200: '#b6d7ff',
          300: '#7fb9ff',
          400: '#4293ff',
          500: '#1b71d3',
          600: '#145bb1',
          700: '#124a8f',
          800: '#123f75',
          900: '#123662',
        },
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}

