/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#008CFF',
          50: '#e6f4ff',
          500: '#008CFF',
          900: '#172755',
        },
        night: '#172755',
        cream: '#FDFBE3',
        white: '#FFFFFF',
      },
      fontFamily: {
        hendrix: ['"BR Hendrix"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
