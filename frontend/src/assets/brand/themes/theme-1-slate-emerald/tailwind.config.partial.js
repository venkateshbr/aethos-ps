/**
 * Theme 1 — Slate + Emerald — partial Tailwind theme extension.
 *
 * Drop into `frontend/tailwind.config.js` under `theme.extend` when this
 * direction is chosen. The structural slate scale already lives in Tailwind's
 * defaults — we only extend the slate-750 custom step and the accent palette.
 */
module.exports = {
  theme: {
    extend: {
      colors: {
        slate: {
          750: '#293548', // raised surface (hovered cards, dropdowns)
        },
        // Brand accent — emerald, doubles as the success / approval semantic
        accent: {
          DEFAULT: '#10b981', // emerald-500
          hover:   '#059669', // emerald-600
          light:   '#34d399', // emerald-400
          subtle:  '#064e3b', // emerald-900
          on:      '#ffffff',
        },
        // HITL confidence chips
        confidence: {
          high: '#10b981',
          med:  '#f59e0b',
          low:  '#ef4444',
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
        card:        '0 1px 0 0 rgba(255,255,255,0.04) inset, 0 1px 2px 0 rgba(0,0,0,0.4)',
        'card-hover':'0 1px 0 0 rgba(255,255,255,0.06) inset, 0 4px 12px 0 rgba(0,0,0,0.45)',
        'accent-ring':'0 0 0 3px rgba(16,185,129,0.25)',
      },
    },
  },
};
