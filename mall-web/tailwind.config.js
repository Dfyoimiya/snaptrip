/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      maxWidth: {
        '7xl': '1200px',
      },
      colors: {
        brand: {
          50: '#fff3ed',
          100: '#ffe0d0',
          200: '#ffd7c2',
          300: '#ffc4a3',
          400: '#ff8a00',
          500: '#ff7900',
          600: '#ff5000',
          700: '#dc2626',
        },
        'bg-page': '#ffffff',
        'text-body': '#1f1f1f',
        'text-sub': '#888888',
        'text-muted': '#bbbbbb',
        'border-subtle': '#f5f5f5',
      },
      borderRadius: {
        'product-img': '12px',
      },
    },
  },
  plugins: [],
}
