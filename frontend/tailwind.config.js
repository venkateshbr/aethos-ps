/**
 * Aethos PS — Tailwind v3 config.
 *
 * Tokens sourced from `src/assets/brand/themes/theme-1-slate-emerald/`
 * (Direction A — founder-picked, issue #9). The structural slate scale
 * already lives in Tailwind's defaults — we only extend the custom
 * `slate-750` raised-surface step plus the brand `accent` and HITL
 * `confidence` palettes.
 *
 * If the brand direction is ever re-picked, swap the partial in:
 *   src/assets/brand/themes/<direction>/tailwind.config.partial.js
 */
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      colors: {
        // Custom raised-surface step (hovered cards, dropdowns)
        slate: {
          750: '#293548',
        },
        // Brand accent — emerald. Doubles as the success / approval
        // semantic so the brand colour and the most common positive
        // in-app signal reinforce each other (see notes.md).
        accent: {
          DEFAULT: '#10b981', // emerald-500
          hover:   '#059669', // emerald-600
          light:   '#34d399', // emerald-400
          subtle:  '#064e3b', // emerald-900
          on:      '#ffffff',
        },
        // HITL confidence chips — bound to the same hexes as the
        // semantic success / warning / error palette so a single
        // visual language carries across agent UI and status badges.
        confidence: {
          high: '#10b981', // ≥ 0.90 (auto-eligible)
          med:  '#f59e0b', // 0.70–0.89 (review)
          low:  '#ef4444', // < 0.70 (mandatory review)
        },
      },
      fontFamily: {
        display: ['Inter', 'system-ui', 'sans-serif'],
        sans:    ['Inter', 'system-ui', 'sans-serif'],
      },
      letterSpacing: {
        brand: '0.04em',
      },
      boxShadow: {
        card:         '0 1px 0 0 rgba(255,255,255,0.04) inset, 0 1px 2px 0 rgba(0,0,0,0.4)',
        'card-hover': '0 1px 0 0 rgba(255,255,255,0.06) inset, 0 4px 12px 0 rgba(0,0,0,0.45)',
        'accent-ring':'0 0 0 3px rgba(16,185,129,0.25)',
      },
      animation: {
        'fade-in': 'fadeIn 0.35s ease-out',
        'blink':   'blink 1s steps(2, start) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0' },
        },
      },
    }
  },
  plugins: []
};
