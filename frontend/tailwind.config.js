/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#0F2038',
          50: '#EEF2F7',
          100: '#D7E0EC',
          600: '#1B3A61',
          700: '#152D4C',
          900: '#0F2038',
        },
        amber: {
          DEFAULT: '#D97706',
          50: '#FEF3E2',
          100: '#FDE3BE',
          600: '#B45F04',
        },
        risk: {
          low: '#15803D',
          moderate: '#CA8A04',
          high: '#EA580C',
          critical: '#B91C1C',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'sans-serif',
        ],
      },
      fontSize: {
        base: ['15px', '1.6'],
      },
      maxWidth: {
        content: '1400px',
      },
    },
  },
  plugins: [],
}
