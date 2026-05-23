# Theme 3 — Carbon + Amber — Palette

> Third direction (not in original DESIGN_BRIEF). Warm, premium, editorial.
> Mood: hand-crafted, considered, the brand of a boutique firm rather than a SaaS company. Carbon (warm near-black) replaces cool slate; amber replaces emerald as the single accent.

## Core surfaces

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `bg-base` | `#161514` | (custom carbon) | App shell — warm near-black (not pure black, not cool slate) |
| `bg-surface` | `#1f1d1b` | (custom) | Cards, panels, modals |
| `bg-surface-raised` | `#2a2825` | (custom) | Hovered cards, dropdowns |
| `bg-surface-sunken` | `#0e0d0c` | (custom) | Code blocks, read-only fields |
| `border-default` | `#3a3733` | (custom) | Card borders, input borders — warm grey, not slate |
| `border-subtle` | `#252320` | (custom) | Internal dividers |

## Text

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `text-primary` | `#fafaf7` | (custom bone) | Headings, primary copy — slightly warm white |
| `text-secondary` | `#d6d3d1` | `stone-300` | Labels, metadata |
| `text-muted` | `#a8a29e` | `stone-400` | Placeholders, captions |

## Accent (primary brand)

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `accent` | `#f5a524` | (custom amber) | Primary buttons, logo mark, the "seal" |
| `accent-hover` | `#d97706` | `amber-600` | Hover state |
| `accent-light` | `#fbbf24` | `amber-400` | Highlights, focus rings |
| `accent-subtle-bg` | `#3a2a08` | (custom) | Subtle accent panels |
| `accent-on` | `#161514` | (carbon) | Text/icon on accent fills (dark on warm-amber) |

## Confidence colours (HITL chips)

Because amber is already the brand colour, "medium confidence" cannot also be amber. We shift the confidence triad warm-cool-warm so each one is unambiguous against carbon.

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `confidence-high` | `#84cc16` | `lime-500` | ≥ 0.90 — warm-green, harmonises with amber but reads distinctly |
| `confidence-med` | `#fb923c` | `orange-400` | 0.70–0.89 — distinct from amber accent, leans warmer |
| `confidence-low` | `#ef4444` | `red-500` | < 0.70 |

> Note: the brand amber and the confidence-medium orange must never sit adjacent to a confidence-high lime without the explicit confidence label visible. Always pair the dot with the numeric score.

## Type pairing

- **Display / wordmark**: Inter SemiBold (`font-weight: 600`), letter-spacing `-0.01em` (tighter than the cool themes — adds editorial weight)
- **UI body**: Inter Regular / Medium
- **Editorial / hero headlines**: GT Sectra or Tiempos Headline (paid) — fallback Source Serif 4 (free)
- **Numeric / tabular**: Inter with `font-variant-numeric: tabular-nums`

## Contrast notes

- `amber (#f5a524) on carbon (#161514)` — 8.4:1 (passes AAA)
- `bone (#fafaf7) on carbon` — 16.9:1 (passes AAA)
- `stone-300 on carbon` — 11.1:1 (passes AAA)
- `lime-500 on carbon` — 10.7:1 (passes AAA)

## Light surface

This palette has a strong light-mode counterpart: bone background, carbon ink, amber accent — reads like a letterpress or fine-stationery printed piece. Useful for PDF invoice templates and printed reports even if the app itself stays dark.
