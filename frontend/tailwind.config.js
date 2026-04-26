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
        // Brand identity: Blue · White · Black · Gray
        primary: {
          DEFAULT: '#2563EB', // blue-600
          50:  '#EFF6FF',     // blue-50
          100: '#DBEAFE',     // blue-100
          200: '#BFDBFE',     // blue-200
          300: '#93C5FD',     // blue-300
          400: '#60A5FA',     // blue-400
          500: '#3B82F6',     // blue-500
          600: '#2563EB',     // blue-600
          700: '#1D4ED8',     // blue-700
          800: '#1E40AF',     // blue-800
          900: '#1E3A8A',     // blue-900
          hover: '#1D4ED8',   // alias for 700
        },
        // Neutral scale (semantic aliases for Tailwind gray)
        neutral: {
          50:  '#F9FAFB',
          100: '#F3F4F6',
          200: '#E5E7EB',
          300: '#D1D5DB',
          400: '#9CA3AF',
          500: '#6B7280',
          600: '#4B5563',
          700: '#374151',
          800: '#1F2937',
          900: '#111827',
        },
        surface: '#FFFFFF',
        background: '#F9FAFB',
        // Semantic status colors (not brand, but functional)
        success: {
          DEFAULT: '#16A34A', // green-600
          light:   '#DCFCE7', // green-100
        },
        warning: {
          DEFAULT: '#D97706', // amber-600
          light:   '#FEF3C7', // amber-100
        },
        danger: {
          DEFAULT: '#DC2626', // red-600
          light:   '#FEE2E2', // red-100
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '0.75rem', // rounded-xl — consistent card radius
      },
      boxShadow: {
        card: '0 1px 3px 0 rgb(0 0 0 / 0.07), 0 1px 2px -1px rgb(0 0 0 / 0.04)',
        'card-hover': '0 4px 12px 0 rgb(0 0 0 / 0.10), 0 2px 4px -2px rgb(0 0 0 / 0.04)',
      },
    },
  },
  plugins: [],
}
