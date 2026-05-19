/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      colors: {
        'slate-ui': {
          900: '#0f172a',
          800: '#1e293b',
          700: '#334155',
          600: '#475569',
        },
        'emerald-confidence': '#10b981',
        'amber-confidence': '#f59e0b',
        'red-confidence': '#ef4444',
      }
    }
  },
  plugins: []
};
