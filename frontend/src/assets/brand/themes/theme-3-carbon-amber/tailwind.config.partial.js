/**
 * Theme 3 — Carbon + Amber — partial Tailwind theme extension.
 *
 * Warm-spectrum alternative: carbon (warm near-black) replaces slate,
 * amber replaces emerald as the single accent. Drop into
 * `frontend/tailwind.config.js` under `theme.extend` if this direction
 * is chosen.
 */
module.exports = {
  theme: {
    extend: {
      colors: {
        carbon: {
          900: '#161514', // base
          800: '#1f1d1b', // surface
          750: '#2a2825', // surface raised
          950: '#0e0d0c', // surface sunken
          700: '#3a3733', // border default
          850: '#252320', // border subtle
        },
        bone: {
          DEFAULT: '#fafaf7', // text primary — warm white
          muted:   '#d6d3d1', // stone-300
          subtle:  '#a8a29e', // stone-400
        },
        accent: {
          DEFAULT: '#f5a524', // brand amber (custom step between amber-400/500)
          hover:   '#d97706', // amber-600
          light:   '#fbbf24', // amber-400
          subtle:  '#3a2a08', // warm amber subtle bg
          on:      '#161514', // carbon — dark on light-amber
        },
        confidence: {
          high: '#84cc16', // lime-500 — distinct from brand amber
          med:  '#fb923c', // orange-400 — distinct from brand amber
          low:  '#ef4444', // red-500
        },
      },
      fontFamily: {
        display: ['Inter', 'system-ui', 'sans-serif'],
        sans:    ['Inter', 'system-ui', 'sans-serif'],
        serif:   ['"Source Serif 4"', 'Georgia', 'serif'],
      },
      letterSpacing: {
        brand: '-0.01em',
        tag:   '0.16em',
      },
      boxShadow: {
        card:        '0 1px 0 0 rgba(255,250,235,0.04) inset, 0 1px 2px 0 rgba(0,0,0,0.45)',
        'card-hover':'0 1px 0 0 rgba(255,250,235,0.06) inset, 0 4px 14px 0 rgba(0,0,0,0.55)',
        'accent-ring':'0 0 0 3px rgba(245,165,36,0.25)',
        seal:        '0 0 24px 0 rgba(245,165,36,0.15)',
      },
    },
  },
};
