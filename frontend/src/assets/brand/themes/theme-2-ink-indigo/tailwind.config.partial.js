/**
 * Theme 2 — Ink + Indigo — partial Tailwind theme extension.
 *
 * Distinct surface stack from Tailwind's default slate — ink is cooler and
 * deeper. Drop into `frontend/tailwind.config.js` under `theme.extend` if
 * this direction is chosen.
 */
module.exports = {
  theme: {
    extend: {
      colors: {
        ink: {
          900: '#0b1020', // base
          800: '#161c33', // surface
          750: '#1f2742', // surface raised
          950: '#070b18', // surface sunken
          700: '#2a3354', // border default
          850: '#1c2440', // border subtle
        },
        paper: {
          DEFAULT: '#f5f5f7', // text primary — warmer than slate-50
          muted:   '#cbd0e0',
          subtle:  '#8b93ad',
        },
        accent: {
          DEFAULT: '#818cf8', // indigo-400
          hover:   '#6366f1', // indigo-500
          light:   '#a5b4fc', // indigo-300
          subtle:  '#1e1b4b', // indigo-950
          on:      '#0b1020', // dark text on light-indigo fills
        },
        confidence: {
          high: '#22d3ee', // cyan-400 — cool-spectrum positive
          med:  '#fbbf24', // amber-400
          low:  '#f87171', // red-400
        },
      },
      fontFamily: {
        display: ['Inter', 'system-ui', 'sans-serif'],
        sans:    ['Inter', 'system-ui', 'sans-serif'],
        serif:   ['"Source Serif 4"', 'Georgia', 'serif'],
      },
      letterSpacing: {
        brand: '0.01em',
        tag:   '0.22em',
      },
      boxShadow: {
        card:        '0 1px 0 0 rgba(255,255,255,0.03) inset, 0 1px 3px 0 rgba(0,0,0,0.5)',
        'card-hover':'0 1px 0 0 rgba(255,255,255,0.05) inset, 0 6px 16px 0 rgba(0,0,0,0.55)',
        'accent-ring':'0 0 0 3px rgba(129,140,248,0.22)',
      },
    },
  },
};
