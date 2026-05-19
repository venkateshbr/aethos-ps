# Aethos for Professional Services — Logo Lockup Design Brief

> **Issue**: #9
> **Owner**: Chitra (Frontend Design Lead)
> **Status**: Awaiting founder selection by Friday Week 1
> **Scope**: Services-specific logo lockup + accent colour. Not a full rebrand — parent Aethos wordmark, type, and dark slate palette are inherited.

---

## Brief Overview

Aethos is the parent brand. This product is **Aethos, for professional services** — positioned in the same Linear-minimalism tradition as the parent: clean, confident, no noise. The lockup must extend the parent mark for a professional services audience (consultancies, dev shops, advisory firms, accounting practices) without fracturing brand coherence.

**Deliverable**: One chosen lockup direction (SVG master file, light/dark/mono variants) produced by a designer using this brief. The SVG goes into `frontend/src/assets/brand/`.

**Decision deadline**: Founder picks one direction by Friday of Week 1.

---

## Direction A — Minimal Wordmark (Recommended)

### Concept

Clean Inter Bold wordmark plus a geometric micro-mark. The mark says "we are precise, modern, and trustworthy" — the same signals professional services firms want to project to their clients. Fastest to ship. Strongest brand recall at small sizes.

### Logotype Treatment

- **Wordmark**: "Aethos" set in **Inter Bold**, tracked at +10 (slightly open — adds authority without being corporate).
- **Micro-mark**: A 14×14pt rotated square (45°) positioned flush-left of the wordmark, vertically centered on the cap-height. The square can be hollow (stroke only) or solid — solid is recommended for favicon use. The geometry implies precision, structure, and the rotated orientation implies forward motion without aggression.
- **Sub-mark text**: None on the primary lockup. On contexts where disambiguation is needed (invoice header, email footer), append **`for professional services`** in Inter Regular 10pt, slate-400, set below the wordmark aligned to its left edge — not part of the primary mark.
- **Clearspace**: 1× the height of the rotated square on all four sides of the combined lockup.

### Recommended Accent Colour

**Emerald-500** — `#10b981`

Semantic meaning in PS context: growth, financial health, approvals, successful billing runs. In a dark slate environment, emerald reads immediately as "positive signal" — exactly the feeling we want when an agent posts a journal, a payment arrives, or an invoice is approved. It is distinct from indigo (used in the parent Aethos product) and from amber (warnings), so it carries unambiguous semantic weight.

Full token set for Direction A (proposed as working defaults in `DESIGN_SYSTEM.md`):

| Token | Hex | Tailwind |
|---|---|---|
| Accent Primary | `#10b981` | `emerald-500` |
| Accent Primary Hover | `#059669` | `emerald-600` |
| Accent Light | `#34d399` | `emerald-400` |
| Accent Subtle BG | `#064e3b` | `emerald-900` |
| Accent On-Accent | `#ffffff` | white |

### Sample Applications

**Dark Sidebar**
Lockup: rotated square (emerald-500 solid) + "Aethos" (white, Inter Bold) + no sub-mark text. At 28px cap-height, the square is 14px. The combination sits in the top 56px rail, left-padded 16px.

**Email Footer**
Lockup: rotated square (emerald-500) + "Aethos" (slate-300, Inter Bold, reduced to 12pt) + `for professional services` (slate-500, Inter Regular, 9pt) stacked below. On `#0f172a` background strip, 24px padding each side. The mark does not exceed 120px wide.

**Invoice Header**
Lockup: rotated square (emerald-500) + "Aethos" (white, 16pt) right-aligned in the top header band. The client's own logo (if tenant has uploaded one) appears left-aligned; Aethos lockup anchors the right. When no tenant logo is set, the Aethos lockup is centered.

**Favicon (16×16, 32×32, 180×180 for Apple Touch)**
Mark only: the rotated square, emerald-500 fill, on `#0f172a` background. No wordmark. At 16px the square is 9px — render as SVG with `shape-rendering: crispEdges`. ICO format wraps all three sizes.

### Pros

1. **Ships fastest** — the geometric micro-mark is a single SVG path; no illustration complexity; a designer can produce all variants in one day.
2. **Strongest recall** — the distinctive rotated square is immediately recognizable at 16px (favicon), 28px (sidebar), and at full print size. Brand recall compounds over time.

### Cons

1. **Most abstract** — the rotated square has no literal reference to professional services or billing. Relies entirely on context and repetition to build meaning.
2. **Risk of geometric cliche** — rotated squares are used in tech brand marks broadly. The uniqueness is in the combination with Inter Bold and emerald on slate, not the shape alone.

---

## Direction B — Services Lockup

### Concept

A two-line stacked treatment that makes the professional-services positioning explicit in the wordmark itself. Targets firms that want to see "professional services" literally in the brand — consultancies presenting to board-level clients, or firms with conservative brand sensibilities. Consultancy-friendly, legible in print.

### Logotype Treatment

- **Primary line**: "Aethos" in Inter Bold, full-weight, 100% size.
- **Secondary line**: "for professional services" in Inter Light or Inter ExtraLight, tracking +20, set at approximately 38% of the primary line's cap-height. Vertically baseline-drops 4px below the primary wordmark.
- **Divider accent**: A horizontal rule — 1px, indigo-500 — spanning the full width of "Aethos" (not of the secondary line), positioned in the 4px gap between the two lines. This is the single graphic element; there is no icon or micro-mark.
- **Stacked lockup height**: approximately 2.2× the cap-height of the primary wordmark.
- The two-line lockup is the primary mark. A horizontal variant (primary line + divider + secondary line in one row, separated by the divider used as a vertical pipe) is the secondary mark for constrained horizontal spaces (invoice header, social card).

### Recommended Accent Colour

**Indigo-500** — `#6366f1`

Semantic meaning: intelligence, trustworthiness, precision, and technology — the signals a management consultancy or finance advisory firm wants to own. In the dark slate environment, indigo-500 is visually calm rather than urgent, which suits the professional-services register. Note: if the parent Aethos brand already uses indigo heavily, the designer should check for collision and consider stepping to indigo-400 (`#818cf8`) for differentiation.

Full token set for Direction B:

| Token | Hex | Tailwind |
|---|---|---|
| Accent Primary | `#6366f1` | `indigo-500` |
| Accent Primary Hover | `#4f46e5` | `indigo-600` |
| Accent Light | `#818cf8` | `indigo-400` |
| Accent Subtle BG | `#1e1b4b` | `indigo-950` |
| Accent On-Accent | `#ffffff` | white |

### Sample Applications

**Dark Sidebar**
Full stacked lockup: "Aethos" (white, Inter Bold) + indigo divider rule + "for professional services" (slate-300, Inter Light). Total height ~42px within a 56px top rail. Left-padded 16px.

**Email Footer**
Horizontal variant: "Aethos" (slate-300) + vertical indigo pipe + "for professional services" (slate-400, Inter Light). On `#0f172a`, 24px padding, max-width 180px.

**Invoice Header**
Horizontal variant, right-aligned. The indigo divider pipe sits between wordmark and services tag. Works at 12–14pt.

**Favicon**
A stylized "A" in Inter Bold, indigo-500, on `#0f172a`. Or a simple double-horizontal-line mark (representing the divider motif) in indigo-500. The "A" monogram is more recognizable but risks looking generic.

### Pros

1. **Explicit positioning** — no ambiguity about what Aethos is for; the secondary line does the targeting work. Ideal for cold outreach contexts where the logo appears before any copy.
2. **Conservative / corporate-safe** — suits law firms, M&A advisory, and CFO-audience buyers who are skeptical of "startup" aesthetics.

### Cons

1. **Longer to execute** — the stacked proportions must be optically corrected by an experienced typographer; letterspacing on the secondary line is fussy.
2. **Poor favicon** — the stacked mark loses its secondary line at 16px; the monogram fallback is less distinctive than Direction A's geometric square.

---

## Direction C — Icon-First

### Concept

A distinctive standalone icon that can carry the brand at any size — 16px favicon, app icon, social avatar — without the wordmark. The icon represents the core value loop of Aethos PS: engagement → billing → payment. Wordmark "Aethos" sits to the right of the icon at full size; the icon stands alone at small sizes. Highest flexibility, highest investment to design correctly.

### Logotype Treatment

- **Icon**: An interconnected triangle motif — three nodes connected by lines forming a triangle, each node representing one stage of the PS cycle (top: engagement / work, bottom-left: billing, bottom-right: payment). The nodes are small filled circles (3–4pt radius at design-scale). The connecting lines are strokes, not fills, slightly rounded at joins.
- **Two-tone rendering**: node circles and triangle strokes in **emerald-400** (`#34d399`); one node (the "payment received" node, bottom-right) filled in **slate-300** (`#cbd5e1`) to differentiate the output node from the two input nodes. This creates a hierarchy within the mark without adding a third colour.
- **Wordmark**: "Aethos" in Inter Bold, to the right of the icon, baseline-aligned to the icon's vertical center. Cap-height of the wordmark = icon height. No sub-mark text in the primary lockup. `for professional services` tag available as optional appendage (same treatment as Direction A).
- **Icon clearspace**: 0.5× icon height on left/right, 0.25× on top/bottom relative to the wordmark.
- **Solo icon form**: icon-only (no wordmark) for favicon, app icon, social avatar, loading spinner.

### Recommended Accent Colours

Two-tone mark: **Emerald-400** (`#34d399`) primary + **Slate-300** (`#cbd5e1`) secondary.

This is intentionally a two-tone system rather than a single accent. The emerald carries the "active / success / AI doing work" signal; slate-300 is neutral enough to represent a completed / settled state without introducing a third semantic colour.

| Token | Hex | Tailwind |
|---|---|---|
| Accent Primary | `#34d399` | `emerald-400` |
| Accent Secondary | `#cbd5e1` | `slate-300` |
| Accent Primary Hover | `#10b981` | `emerald-500` |
| Accent Subtle BG | `#064e3b` | `emerald-900` |
| Accent On-Accent | `#0f172a` | `slate-900` |

Note: emerald-400 on slate-900 has a contrast ratio of approximately 7.2:1, exceeding WCAG AA for normal text. Slate-300 on slate-900 is approximately 7.6:1. Both pass.

### Sample Applications

**Dark Sidebar**
Icon (24px, two-tone) + "Aethos" (white, Inter Bold, 18pt) in a horizontal lockup. The icon's emerald nodes glow subtly via a 4px blur drop-shadow at `rgba(52, 211, 153, 0.3)` — very subtle, not a neon effect.

**Email Footer**
Icon (16px) + "Aethos" (slate-300, 11pt) horizontal. Keeps the email header from feeling like plain text. Two-tone holds at 16px if the icon is SVG (no rasterization).

**Invoice Header**
Full lockup right-aligned. The interconnected triangle at 24px is large enough to read as a "seal" or quality mark on the invoice — positive connotation for the recipient.

**Favicon**
Icon-only at 16×16: the three nodes and triangle strokes. At 16px in SVG the strokes should be 1.5px and the node circles 2px radius. The emerald fill on slate-900 reads clearly even at this size. Provide a 32px and 180px version with proportionally slightly heavier strokes.

### Pros

1. **Maximum flexibility** — the standalone icon works as an app icon, social avatar, loading spinner, and watermark; it is not text-dependent, so it scales to zero-copy contexts.
2. **Conceptually rich** — the triangle motif communicates the PS value chain (engage → bill → collect) to anyone who pauses long enough to read it; design partners will find it meaningful and specific.

### Cons

1. **Hardest to execute** — the interconnected triangle must be optically balanced by a skilled illustrator; done poorly it looks like a generic network diagram or a React logo. Budget at least 2 design iterations.
2. **Risk of over-complexity at 16px** — if the strokes are too thin or the nodes too small, the favicon degrades to a green smudge. Requires explicit favicon QA at 16px actual-rendered size on a retina display, a non-retina display, and a Windows Chrome dark-mode tab.

---

## Recommendation

**Direction A** is the default recommendation for Week 1 ship.

Rationale:
- Fastest to produce (one SVG path, no illustration).
- Cleanest at all sizes including the 16px favicon.
- The emerald-500 accent integrates immediately with the HITL success state, approval badges, and payment-received indicators in the app — the brand colour is also the product's semantic success colour, which is a strong coherence win.
- Easiest for Rupa to implement as CSS variables and Tailwind config on Day 1.

Directions B and C are viable for a v1.1 brand refresh once we have design-partner feedback on what resonates with the buyer.

---

## Usage Rules (all directions)

1. Never place the lockup on a background lighter than `slate-800`. The mark is designed for dark contexts only.
2. Never recolour the wordmark to the accent colour — "Aethos" is always white (`slate-50`) or slate-300. Colour in the lockup lives in the mark element only (micro-mark, divider, icon).
3. Minimum rendered size: 80px wide for the horizontal lockup; 16px for the icon-only / favicon form.
4. No drop shadows on the wordmark. The micro-mark or icon may use a very subtle glow (single-colour, low opacity) in product UI only — never in print or PDF.
5. The `for professional services` sub-tag is optional in all directions. It appears in contexts where disambiguation is needed (cold email footer, invoice, landing page header). It does not appear in app sidebar (space-constrained) or at sizes below 100px wide.

---

## Changelog

### 2026-05-19 — Initial design brief
- Authored by Chitra for Issue #9
- 3 directions specified: A (Minimal Wordmark), B (Services Lockup), C (Icon-First)
- Direction A recommended as Week 1 default
- Accent colour tokens proposed for all three directions
- Direction A tokens written into DESIGN_SYSTEM.md as provisional working defaults
