# Theme 2 — Ink + Indigo — Palette

> Direction B from `DESIGN_BRIEF.md`. Stacked wordmark with explicit positioning.
> Mood: calm, premium, consultancy-grade. The accent (indigo-400) reads as intelligence + trust without urgency.

## Core surfaces

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `bg-base` | `#0b1020` | (custom ink) | App shell — slightly cooler / deeper than slate-900 |
| `bg-surface` | `#161c33` | (custom) | Cards, panels, modals |
| `bg-surface-raised` | `#1f2742` | (custom) | Hovered cards, dropdowns |
| `bg-surface-sunken` | `#070b18` | (custom) | Code blocks, read-only fields |
| `border-default` | `#2a3354` | (custom) | Card borders, input borders |
| `border-subtle` | `#1c2440` | (custom) | Internal dividers |

## Text

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `text-primary` | `#f5f5f7` | (custom paper) | Headings, primary copy — warmer white than slate-50 |
| `text-secondary` | `#cbd0e0` | (custom) | Labels, metadata |
| `text-muted` | `#8b93ad` | (custom) | Placeholders, captions |

## Accent (primary brand)

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `accent` | `#818cf8` | `indigo-400` | Primary buttons, divider rule, links |
| `accent-hover` | `#6366f1` | `indigo-500` | Hover state |
| `accent-light` | `#a5b4fc` | `indigo-300` | Highlights, focus rings |
| `accent-subtle-bg` | `#1e1b4b` | `indigo-950` | Subtle accent panels |
| `accent-on` | `#0b1020` | (ink) | Text/icon on accent fills (dark on light accent) |

## Confidence colours (HITL chips)

Distinct from the brand — green stays green, amber stays amber, red stays red, so semantic meaning is unambiguous against indigo.

| Token | Hex | Tailwind | Usage |
|---|---|---|---|
| `confidence-high` | `#22d3ee` | `cyan-400` | ≥ 0.90 — cyan reads "positive" but does not collide with indigo |
| `confidence-med` | `#fbbf24` | `amber-400` | 0.70–0.89 |
| `confidence-low` | `#f87171` | `red-400` | < 0.70 |

> Note: this theme uses **cyan** for high confidence instead of emerald, to keep all three confidence tones in the cool-spectrum family with the indigo brand. Optional: revert to emerald-400 if the founder prefers warm-green for "approved".

## Type pairing

- **Display / wordmark — primary line**: Inter Bold (`font-weight: 700`), letter-spacing `+0.01em`
- **Display — secondary line (services tag)**: Inter Light (`font-weight: 300`), letter-spacing `+0.22em`, UPPERCASE
- **UI body**: Inter Regular / Medium
- **Serif accent (optional)**: Source Serif 4 for invoice headers and report cover-sheets — adds editorial weight without infiltrating the UI

## Contrast notes

- `indigo-400 on ink (#0b1020)` — 6.5:1 (passes AA for normal text)
- `paper (#f5f5f7) on ink` — 17.4:1 (passes AAA)
- `slate-300 equivalent on ink` — 10.1:1 (passes AAA)
