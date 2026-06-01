/**
 * Aethos PS — Tailwind v3 config.
 *
 * SEMANTIC THEME TOKENS (issue #120 phase 1)
 * ------------------------------------------
 * Every `surface-*`, `border-*`, `text-*` (theme), `accent*`, `confidence-*`
 * utility below resolves to `rgb(var(--t-X) / <alpha-value>)`. The runtime
 * theme picker writes `data-theme="..."` on <body>, which switches the
 * `--t-*` triples defined in `src/styles.scss` and re-skins every component
 * that uses these utilities.
 *
 * `<alpha-value>` is Tailwind's opacity placeholder — it composes correctly
 * with `bg-accent/20`, `text-confidence-med/80`, etc.
 *
 * Legacy literal palettes (`slate.750`, `accent.*`, `confidence.*`) are kept
 * so feature pages that haven't been migrated yet keep rendering. Those
 * pages are theme-blind until the phase-2 follow-up migrates them.
 */
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}", "./projects/**/*.{html,ts}"],
  theme: {
    extend: {
      colors: {
        // ── Theme-aware semantic tokens (read from CSS vars) ──────────
        // Surfaces
        'surface-base':   'rgb(var(--t-bg-base) / <alpha-value>)',
        'surface':        'rgb(var(--t-bg-surface) / <alpha-value>)',
        'surface-raised': 'rgb(var(--t-bg-surface-raised) / <alpha-value>)',
        'surface-sunken': 'rgb(var(--t-bg-surface-sunken) / <alpha-value>)',
        // Borders
        'border-default': 'rgb(var(--t-border-default) / <alpha-value>)',
        'border-subtle':  'rgb(var(--t-border-subtle) / <alpha-value>)',
        'border-strong':  'rgb(var(--t-border-strong) / <alpha-value>)',
        // Text
        'text-primary':   'rgb(var(--t-text-primary) / <alpha-value>)',
        'text-secondary': 'rgb(var(--t-text-secondary) / <alpha-value>)',
        'text-muted':     'rgb(var(--t-text-muted) / <alpha-value>)',
        'text-subtle':    'rgb(var(--t-text-muted) / <alpha-value>)',
        'text-disabled':  'rgb(var(--t-text-disabled) / <alpha-value>)',
        'text-inverse':   'rgb(var(--t-text-inverse) / <alpha-value>)',
        // Accent
        'accent':         'rgb(var(--t-accent) / <alpha-value>)',
        'accent-hover':   'rgb(var(--t-accent-hover) / <alpha-value>)',
        'accent-light':   'rgb(var(--t-accent-light) / <alpha-value>)',
        'accent-subtle':  'rgb(var(--t-accent-subtle-bg) / <alpha-value>)',
        'accent-on':      'rgb(var(--t-accent-on-accent) / <alpha-value>)',
        // HITL confidence chips
        'confidence-high':    'rgb(var(--t-confidence-high) / <alpha-value>)',
        'confidence-high-bg': 'rgb(var(--t-confidence-high-bg) / <alpha-value>)',
        'confidence-med':     'rgb(var(--t-confidence-med) / <alpha-value>)',
        'confidence-med-bg':  'rgb(var(--t-confidence-med-bg) / <alpha-value>)',
        'confidence-low':     'rgb(var(--t-confidence-low) / <alpha-value>)',
        'confidence-low-bg':  'rgb(var(--t-confidence-low-bg) / <alpha-value>)',

        // ── Legacy literal tokens (KEEP — unmigrated pages depend on these) ──
        // Custom raised-surface step (hovered cards, dropdowns)
        slate: {
          750: '#293548',
        },
        // Brand accent — emerald. Doubles as the success / approval
        // semantic so the brand colour and the most common positive
        // in-app signal reinforce each other (see notes.md).
        // NOTE: this `accent.*` namespace is the LEGACY literal hex.
        // The new theme-aware `accent` / `accent-hover` / `accent-light`
        // utilities above take precedence when used as flat names.
        'accent-legacy': {
          DEFAULT: '#10b981', // emerald-500
          hover:   '#059669', // emerald-600
          light:   '#34d399', // emerald-400
          subtle:  '#064e3b', // emerald-900
          on:      '#ffffff',
        },
        // HITL confidence chips — bound to the same hexes as the
        // semantic success / warning / error palette so a single
        // visual language carries across agent UI and status badges.
        // Legacy literal; migrated pages should use `confidence-high|med|low`.
        'confidence-legacy': {
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
        'accent-ring':'0 0 0 3px rgb(var(--t-accent) / 0.25)',
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
