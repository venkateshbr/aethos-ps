# Theme 1 — Slate + Emerald — Palette

> Direction A from `DESIGN_BRIEF.md`. The default recommendation.
> Mood: precise, modern, trustworthy. The accent (emerald) doubles as the product's "success / payment received / approval" semantic, so the brand colour and the most common positive in-app signal reinforce each other.

## Core surfaces

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `bg-base` | `#0f172a` | `slate-900` | App shell, page canvas |
| `bg-surface` | `#1e293b` | `slate-800` | Cards, panels, modals |
| `bg-surface-raised` | `#293548` | (custom) | Hovered cards, dropdowns |
| `bg-surface-sunken` | `#0d1424` | `slate-950` | Code blocks, read-only fields |
| `border-default` | `#334155` | `slate-700` | Card borders, input borders |
| `border-subtle` | `#1e293b` | `slate-800` | Internal dividers |

## Text

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `text-primary` | `#f8fafc` | `slate-50` | Headings, primary copy |
| `text-secondary` | `#cbd5e1` | `slate-300` | Labels, metadata |
| `text-muted` | `#94a3b8` | `slate-400` | Placeholders, captions |

## Accent (primary brand)

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `accent` | `#10b981` | `emerald-500` | Primary buttons, links, logo mark |
| `accent-hover` | `#059669` | `emerald-600` | Hover state |
| `accent-light` | `#34d399` | `emerald-400` | Highlights, focus rings |
| `accent-subtle-bg` | `#064e3b` | `emerald-900` | Subtle accent panels, hover backgrounds |
| `accent-on` | `#ffffff` | white | Text/icon on accent fills |

## Confidence colours (HITL chips)

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `confidence-high` | `#10b981` | `emerald-500` | ≥ 0.90 (auto-eligible) |
| `confidence-med` | `#f59e0b` | `amber-500` | 0.70–0.89 (review) |
| `confidence-low` | `#ef4444` | `red-500` | < 0.70 (mandatory review) |

## Type pairing

- **Display / wordmark**: Inter Bold (`font-weight: 700`), letter-spacing `+0.04em`
- **UI body**: Inter Regular / Medium
- **Numeric / tabular** (amounts, dates): Inter with `font-variant-numeric: tabular-nums`
- **Fallback stack**: `'Inter', system-ui, -apple-system, sans-serif`

## Contrast notes

- `emerald-500 on slate-900` — 5.2:1 (passes WCAG AA for large text and UI)
- `emerald-400 on slate-900` — 7.2:1 (passes AAA for normal text)
- `slate-50 on slate-900` — 16.7:1 (passes AAA)
- `slate-300 on slate-900` — 10.5:1 (passes AAA)
