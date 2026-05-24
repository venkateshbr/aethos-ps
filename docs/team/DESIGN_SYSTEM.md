# Aethos for Professional Services — Design System

> **Owner**: Chitra (Frontend Design Lead)
> **Status**: Living document — updated as components and tokens evolve
> **Tech surface**: Angular 19 + Tailwind v3 + Angular Material 19 (dark theme override)

---

## Design Principles

1. **Dark theme, always** — slate-900 background, slate-800 cards, slate-700 borders. No light surfaces in the app shell.
2. **Information density done right** — PS users need data, but it must be scannable. Prefer structured data tables with clear hierarchy over card grids for list views.
3. **Agent transparency** — users always know when AI is acting and can override. Every AI-generated field carries a wand icon and a confidence indicator. No silent agent actions.
4. **Consistency over novelty** — every component derives from this system. No one-off colours, sizes, or spacing values.
5. **Mobile-aware, desktop-first** — primary users are desktop/laptop (finance, consulting). Mobile breakpoints exist for notifications and approvals on the go.

---

## Tokens

> **Direction A — Slate + Emerald — finalised on 2026-05-24** (issue #9 selection).
> Source of truth for token hexes: `frontend/src/assets/brand/themes/theme-1-slate-emerald/`.
> Live in code at: `frontend/tailwind.config.js` (Tailwind utilities) and `frontend/src/styles.scss` (CSS custom properties `--t-*`).

### Background & Surface

| Token (CSS var) | Hex | Tailwind | Usage |
|---|---|---|---|
| `--t-bg-base` | `#0f172a` | `slate-900` | App shell background, page canvas |
| `--t-bg-surface` | `#1e293b` | `slate-800` | Cards, panels, modals, drawers |
| `--t-bg-surface-raised` | `#293548` | `slate-750` (custom) | Hover state on cards, dropdown backgrounds |
| `--t-bg-surface-sunken` | `#0d1424` | `slate-950` | Code blocks, read-only fields, data table stripe |
| `--t-bg-overlay` | `rgba(15,23,42,0.80)` | — | Modal/drawer backdrop |

Note: `slate-750` is not a native Tailwind step. Define in `tailwind.config.js` as `750: '#293548'` under `colors.slate`.

### Border

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `--t-border-default` | `#334155` | `slate-700` | Card borders, input borders, dividers |
| `--t-border-subtle` | `#1e293b` | `slate-800` | Subtle separators within a surface |
| `--t-border-strong` | `#475569` | `slate-600` | Focus rings (before focus-specific token overrides), active states |

### Text

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `--t-text-primary` | `#f8fafc` | `slate-50` | Headings, primary body copy, data values |
| `--t-text-secondary` | `#cbd5e1` | `slate-300` | Secondary labels, timestamps, metadata |
| `--t-text-muted` | `#94a3b8` | `slate-400` | Placeholder text, captions, helper text |
| `--t-text-disabled` | `#475569` | `slate-600` | Disabled form fields, inactive nav items |
| `--t-text-inverse` | `#0f172a` | `slate-900` | Text on accent-coloured backgrounds |

### Accent Colour (Direction A — Emerald — selected)

> **Brand accent doubles as the in-app "success / approval / payment-received" semantic.** This is a deliberate coherence win — when an agent posts a journal or a payment lands, the brand colour fires. The trade-off is documented in `frontend/src/assets/brand/themes/theme-1-slate-emerald/notes.md`: we cannot later introduce a green semantic distinct from the brand without pivoting both at once.

| Token (CSS var) | Tailwind utility | Hex | Usage |
|---|---|---|---|
| `--t-accent` / `--brand-primary` | `bg-accent` `text-accent` `border-accent` | `#10b981` | Primary action buttons, links, brand mark micro-element, active nav indicator |
| `--t-accent-hover` / `--brand-primary-hover` | `bg-accent-hover` `hover:bg-accent-hover` | `#059669` | Hover state on accent-coloured elements |
| `--t-accent-light` / `--brand-primary-light` | `text-accent-light` `border-accent-light` | `#34d399` | Accent on text (use in place of `--t-accent` for body copy contrast), icon fills, focus rings |
| `--t-accent-subtle-bg` / `--brand-primary-subtle` | `bg-accent-subtle` | `#064e3b` | Subtle background tint for success states, selected rows, approved-badge backgrounds |
| `--t-accent-on-accent` / `--brand-on-primary` | `text-accent-on` | `#ffffff` | Text / icons on `--t-accent` filled backgrounds |

### Brand Lockup

The Aethos PS lockup pairs a rotated-square mark (14×14, emerald-500, 1.5px radius, rotated 45°) with the wordmark "Aethos" in Inter Bold + 0.04em letter-spacing, over a sub-mark "for professional services" in Inter Regular 11px + 0.18em letter-spacing + slate-400.

| File | Purpose |
|---|---|
| `frontend/src/assets/brand/lockup.svg` | Full lockup (mark + wordmark + sub-mark). Use in landing header, signup hero, emails, marketing. |
| `frontend/src/assets/brand/mark.svg` | Mark only (rotated square). Use as favicon, app icon, sidebar logo when collapsed. |
| `frontend/public/favicon.svg` | Browser tab favicon (modern browsers). |
| `frontend/public/favicon.ico` | Fallback favicon (legacy browsers, `/favicon.ico` auto-requests). |

**Inline micro-mark pattern**: For sidebar logos and inline brand chips, the rotated square can be reproduced with Tailwind utilities instead of importing the SVG:

```html
<span class="lockup-mark inline-block w-3.5 h-3.5 bg-accent rounded-[2px]" aria-hidden="true"></span>
```

`lockup-mark` is a tiny global class in `styles.scss` that applies `transform: rotate(45deg)`.

**Source of truth**: `frontend/src/assets/brand/themes/theme-1-slate-emerald/` — palette spec, mockup, theme partial, lockup, and design notes.

### Confidence Chips (HITL agent UI)

Confidence pills appear on every agent-generated suggestion in the inbox and on suggestion cards in the copilot. The pill uses the same hex as the corresponding semantic (success / warning / error) so the visual language carries across.

| Confidence band | Tailwind utility | CSS var | Hex | Rule |
|---|---|---|---|---|
| `≥ 0.90` (auto-eligible) | `bg-confidence-high` `text-confidence-high` | `--t-confidence-high` | `#10b981` | Agent can act at L3 if autonomy permits |
| `0.70 – 0.89` (review) | `bg-confidence-med` `text-confidence-med` | `--t-confidence-med` | `#f59e0b` | Surface as HITL task; one-click approve |
| `< 0.70` (mandatory review) | `bg-confidence-low` `text-confidence-low` | `--t-confidence-low` | `#ef4444` | Block auto-action; require human edit |

Pill background convention: `bg-accent-subtle` (or `bg-amber-900/40` / `bg-red-900/40` for med/low) with `text-confidence-*` foreground — gives a dim glow on the slate-900 surface rather than a solid fill that would over-weight the row.

**Contrast on `slate-900`** (`#0f172a`):
- `confidence-high` `#10b981` → 5.2:1 (passes WCAG AA for large text and UI components)
- `confidence-med`  `#f59e0b` → 7.6:1 (passes AAA for normal text)
- `confidence-low`  `#ef4444` → 4.9:1 (passes AA for normal text)
- `accent-light`    `#34d399` → 7.2:1 (passes AAA — preferred for body copy in green)

No hex adjustments were required from the `palette.md` spec — the founder-picked palette already meets WCAG AA on every confidence chip / accent pair against the slate-900 canvas.

### Semantic Colours

| Token | Hex | Tailwind | Semantic |
|---|---|---|---|
| `--t-success` | `#10b981` | `emerald-500` | Approved, paid, posted, healthy |
| `--t-success-light` | `#34d399` | `emerald-400` | Success icon on dark background |
| `--t-success-bg` | `#064e3b` | `emerald-900` | Success badge / pill background |
| `--t-warning` | `#f59e0b` | `amber-500` | Pending HITL, low confidence, stale FX rate |
| `--t-warning-light` | `#fbbf24` | `amber-400` | Warning icon |
| `--t-warning-bg` | `#451a03` | `amber-950` | Warning badge background |
| `--t-error` | `#ef4444` | `red-500` | Rejected, failed, validation error, period locked |
| `--t-error-light` | `#f87171` | `red-400` | Error icon |
| `--t-error-bg` | `#450a0a` | `red-950` | Error badge background |
| `--t-info` | `#6366f1` | `indigo-500` | Informational, agent suggestions, AI context |
| `--t-info-light` | `#818cf8` | `indigo-400` | Info icon |
| `--t-info-bg` | `#1e1b4b` | `indigo-950` | Info badge background |

### Typography

Type pairing inherited from parent Aethos brand.

| Role | Family | Weight | Size | Line Height |
|---|---|---|---|---|
| Display | Inter | 800 (ExtraBold) | 2.25rem (36px) | 1.2 |
| Heading 1 | Inter | 700 (Bold) | 1.5rem (24px) | 1.3 |
| Heading 2 | Inter | 600 (SemiBold) | 1.125rem (18px) | 1.4 |
| Heading 3 | Inter | 600 (SemiBold) | 0.875rem (14px) | 1.4 |
| Body | Inter | 400 (Regular) | 0.875rem (14px) | 1.5 |
| Body Small | Inter | 400 (Regular) | 0.75rem (12px) | 1.5 |
| Mono / Code | JetBrains Mono | 400 | 0.8125rem (13px) | 1.5 |
| Label | Inter | 500 (Medium) | 0.75rem (12px) | 1.3 |

Numeric data (amounts, hours, rates) uses `JetBrains Mono` at body size — tabular-nums ensures column alignment in data tables.

### Spacing Scale

Standard Tailwind spacing scale applies. Key values used in app layout:

| Use | Value |
|---|---|
| Sidebar width (expanded) | 240px |
| Sidebar width (collapsed) | 56px |
| Top nav height | 56px |
| Page horizontal padding | 24px (md), 32px (lg+) |
| Card inner padding | 16px (sm card), 24px (standard card) |
| Section gap | 24px |
| Form field gap | 16px |
| Inline element gap | 8px |

### Radius

| Context | Value |
|---|---|
| Buttons, inputs, chips, badges | 6px |
| Cards, modals, drawers | 8px |
| Popovers, tooltips | 4px |
| Icon-only buttons | 6px |
| Avatar | 50% (circular) |

---

## Component Patterns

### Buttons

**Primary**: `--t-accent` fill, `--t-accent-on-accent` text. Hover: `--t-accent-hover`. Height 36px, padding 0 16px, radius 6px, Inter Medium 14px. No uppercase.

**Secondary**: Transparent fill, `--t-border-default` border 1px, `--t-text-secondary` text. Hover: `--t-bg-surface-raised` fill, `--t-border-strong` border.

**Destructive**: `--t-error` fill on hover / confirm state. Default state matches Secondary to avoid premature alarm.

**Ghost**: No border, no fill. `--t-text-secondary` text. Hover: `--t-bg-surface-raised`. Used for less critical actions in data tables.

**Icon-only button**: 36×36px, radius 6px. Follow Ghost or Secondary styles.

All interactive states: `hover`, `focus-visible` (2px `--t-accent` outline, 2px offset), `active` (1px inset shadow), `disabled` (40% opacity, cursor not-allowed).

### Badges / Pills

Compact status indicators. Height 20px, padding 0 8px, radius 6px, Label typography.

| Variant | Text colour | Background |
|---|---|---|
| Success | `--t-success-light` | `--t-success-bg` |
| Warning | `--t-warning-light` | `--t-warning-bg` |
| Error | `--t-error-light` | `--t-error-bg` |
| Info | `--t-info-light` | `--t-info-bg` |
| Neutral | `--t-text-muted` | `--t-bg-surface-raised` |

### Data Tables

- Background: `--t-bg-base` (not surface — tables float on the page canvas).
- Header row: `--t-bg-surface`, `--t-text-muted`, Label typography, `--t-border-default` bottom border.
- Body rows: alternating `--t-bg-base` / `--t-bg-surface-sunken` for stripe effect. Row height 44px.
- Hover row: `--t-bg-surface-raised`.
- Selected row: `--t-accent-subtle-bg`, left accent border 2px `--t-accent`.
- Sticky first column for wide tables (engagement name, client name).
- AI-suggested values: show `wand` icon (16px, `--t-info-light`) inline after the value with a tooltip "Suggested by AI — click to review".
- Monetary columns: right-aligned, JetBrains Mono.

### Forms

- Input height: 36px.
- Label: Body Small, `--t-text-secondary`, 4px above input.
- Helper text: Body Small, `--t-text-muted`, 4px below input.
- Error text: Body Small, `--t-error-light`, 4px below input, icon `alert-circle` 12px prepended.
- Border: `--t-border-default`. Focus: `--t-accent` 1.5px, no outline (input border becomes accent).
- Read-only / disabled: `--t-bg-surface-sunken` fill, `--t-text-disabled` text, `--t-border-subtle` border.

### Agent / AI UI Patterns

These patterns are critical to Aethos PS's design identity.

**Confidence Meter**
A horizontal bar, 4px height, radius 2px. Track background: `--t-bg-surface-raised`. Fill colour:
- ≥ 0.85: `--t-success` (emerald-500)
- 0.65–0.84: `--t-warning` (amber-500)
- < 0.65: `--t-error` (red-500)
Label: "Confidence: 78%" in Body Small, `--t-text-muted`, trailing the bar.

**HITL Review Card**
Card on `--t-bg-surface`, `--t-border-default` border, 8px radius. Inner layout:
- Top row: agent name + confidence meter + timestamp (slate-400, 11px).
- Body: extracted data in a two-column grid (label / value), AI-filled values shown with `--t-info` left border accent (2px).
- Action row: [Approve] (Primary button), [Edit] (Secondary), [Reject] (Ghost, `--t-error-light` text). Always all three visible.
- Collapsed state: single row with entity type, confidence pill, and an expand chevron. Keyboard shortcut `A` to approve, `E` to edit, `R` to reject when card has focus.

**Agent Activity Feed**
- Each activity item: 40px row, left icon (16px), body text (Body, `--t-text-primary`), trailing timestamp (Body Small, `--t-text-muted`).
- Tool-call in progress: icon is a spinner (16px, `--t-info-light`); row has `--t-info-bg` left border accent 2px.
- Completed tool-call: icon is the tool's static icon (e.g., `file-text` for document extraction); border accent `--t-success`.
- Streaming text: trailing cursor `|` blinks at 1s interval, `--t-accent` colour.

**Wand Indicator**
A 14×14px wand icon (`✦` symbol or a custom SVG) in `--t-info-light` placed inline after AI-suggested field values. Tooltip on hover: "Suggested by [agent name] — confidence [n]%". Clicking the icon opens the source panel (HITL review card).

---

## Accessibility Standards

Minimum WCAG 2.1 AA compliance required across all screens.

| Check | Requirement |
|---|---|
| Text contrast | 4.5:1 minimum for body text; 3:1 for large text (24px+ or 18.67px+ bold) |
| Interactive element contrast | 3:1 for UI component boundaries |
| Focus indicator | 2px `--t-accent` outline, 2px offset — visible on all interactive elements |
| Keyboard navigation | All interactive elements reachable and operable via keyboard |
| ARIA labels | All icon-only buttons have `aria-label`. All data tables have `caption` or `aria-label`. |
| Colour not sole differentiator | All semantic states (success/warning/error) use colour + icon + text label |
| Motion | Respect `prefers-reduced-motion`. All transitions wrap in `@media (prefers-reduced-motion: no-preference)` |

Contrast checks for core token pairs:
- `slate-50` on `slate-900`: **15.3:1** (pass)
- `slate-300` on `slate-900`: **7.6:1** (pass)
- `slate-400` on `slate-900`: **4.6:1** (pass, just)
- `emerald-500` on `slate-900`: **~4.7:1** (pass for UI elements; use `emerald-400` for body text)
- `emerald-400` on `slate-900`: **7.2:1** (pass)
- `amber-400` on `slate-900`: **8.1:1** (pass)
- `red-400` on `slate-900`: **4.9:1** (pass)

---

## Dark Theme Implementation

All components use CSS custom properties (`var(--t-*)`) rather than Tailwind utility classes directly wherever a value maps to a theme token. This allows:
1. A future light-theme variant without rewriting component templates.
2. Per-tenant brand colour overrides (v1.1 feature).

Tailwind utilities are used for layout (spacing, flex, grid) and one-off values not covered by the token system.

Angular Material theme override: define a custom Angular Material theme file (`src/theme.scss`) that maps Material design tokens to the Aethos dark palette. Do not use Angular Material's default purple/blue theme anywhere in the product.

---

## Changelog

### 2026-05-24 — Direction A (Slate + Emerald) finalised — issue #89

- Founder selected `theme-1-slate-emerald` on issue #9. Direction A is now the canonical brand direction.
- `frontend/tailwind.config.js` updated: nested `accent.*` (`accent` / `hover` / `light` / `subtle` / `on`), `confidence.*` (`high` / `med` / `low`), `slate.750` custom step, brand `boxShadow` (`card` / `card-hover` / `accent-ring`), `letterSpacing.brand` (0.04em), `fontFamily.display` (Inter), and a missing `blink` keyframe.
- Legacy flat tokens removed: `slate-ui-{900,800,700,600}`, `emerald-confidence`, `amber-confidence`, `red-confidence`. None were referenced by component templates (grep returned zero matches).
- `frontend/src/styles.scss` exposes the same hexes as CSS custom properties under both the `--t-*` and `--brand-*` namespaces.
- Lockup wired: full `lockup.svg` on the landing header / footer + sidebar wordmark; standalone `mark.svg` for collapsed sidebar and favicon. ICO + SVG favicons added under `frontend/public/`.
- "Brand Lockup" section + "Confidence Chips" section added above.
- Provisional-defaults notice removed — palette is final.

### 2026-05-19 — Initial design system creation
- Document created by Chitra for Issue #9.
- Token table populated with Direction A (Emerald) provisional working defaults from `DESIGN_BRIEF.md`.
- Background, text, border, semantic, typography, spacing, radius tokens defined.
- Core component patterns documented: Buttons, Badges, Data Tables, Forms, Agent/AI UI Patterns.
- Accessibility standards and contrast ratios documented.
- Dark theme implementation guidance added.
- Pending: Founder picks logo direction by Friday → accent tokens finalised; Rupa implements Tailwind config and Angular Material theme.
