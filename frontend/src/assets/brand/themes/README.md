# Aethos — Brand Theme Directions

> **Owner**: Chitra (Frontend Design Lead)
> **Issue**: #9 — "Deliver 2-3 services-specific logo lockup directions"
> **For**: Founder selection. Open all three mockup pages in browser tabs, pick one.
> **Last updated**: 2026-05-23

---

## How to review

1. Open each direction's `mockup.html` in a separate browser tab — no Angular dev server needed; each file is self-contained and loads Tailwind via CDN.
2. Each mockup includes the same four moments: copilot empty state, HITL inbox card with confidence chips, invoice list, and signup hero. Compare like-for-like across themes.
3. Read each direction's `notes.md` for the mood / buyer / trade-off pitch.
4. Pick one. Reply on issue #9 with the name (`theme-1-slate-emerald`, `theme-2-ink-indigo`, or `theme-3-carbon-amber`) and we wire it into `tailwind.config.js` and component styles.

Mockup paths (open in browser):
- [`theme-1-slate-emerald/mockup.html`](theme-1-slate-emerald/mockup.html)
- [`theme-2-ink-indigo/mockup.html`](theme-2-ink-indigo/mockup.html)
- [`theme-3-carbon-amber/mockup.html`](theme-3-carbon-amber/mockup.html)

---

## Side-by-side

| | **Theme 1 — Slate + Emerald** | **Theme 2 — Ink + Indigo** | **Theme 3 — Carbon + Amber** |
|---|---|---|---|
| **Mood** | Precise, modern, trustworthy | Quiet authority, premium calm | Warm, considered, boutique-craft |
| **Background** | Cool slate-900 (`#0f172a`) | Deeper cool ink (`#0b1020`) | Warm carbon (`#161514`) |
| **Accent** | Emerald-500 (`#10b981`) | Indigo-400 (`#818cf8`) | Brand amber (`#f5a524`) |
| **Wordmark weight** | Inter Bold, tracked +0.04em | Inter Bold, near-default tracking | Inter SemiBold, tracked -0.01em |
| **Mark** | 14×14 rotated square, solid | Stacked wordmark + 1.5px indigo rule, no mark | Circle + amber dot — reads as a wax seal |
| **Sub-mark text** | "for professional services" optional, all-caps tag | "for professional services" *part of* the lockup | "for professional services" optional, all-caps tag |
| **Headline type** | Inter Bold | Source Serif 4 / GT Sectra (editorial) | Source Serif 4 (editorial, italic accent) |
| **Confidence triad** | emerald / amber / red | cyan / amber / red (cool-spectrum) | lime / orange / red (warm-spectrum) |
| **Favicon viability** | Excellent — square mark at 16px | Weak — stacked lockup degrades; needs monogram fallback | Good — solid amber dot at 16px |
| **Buyer fit** | Modern consultancies, dev shops, advisory firms | M&A advisory, accounting / law, board-audience | Boutique firms, design-led agencies, family offices |
| **Day-1 ship cost** | ~1 design day (lowest) | ~2-3 days (typographic fussiness) | ~2 days (mark + serif pairing) |
| **Differentiation risk** | Lowest — most familiar register | Medium — indigo is crowded in B2B | Highest — but the most distinctive of the three |
| **Trade-off** | Brand colour = success semantic (cannot diverge later) | Loses secondary line below 32px | High variance in buyer reaction — bet on personality |

---

## When to pick which

**Pick Theme 1 — Slate + Emerald** if:
- You want to ship the brand in one design day and start building the product.
- The buyer is a tech-forward consultancy or dev shop that already uses Linear, Notion, Vercel.
- You value semantic coherence (brand colour = success colour) over distinctiveness.
- You want the lowest-risk pick that still looks premium against legacy ERPs.

**Pick Theme 2 — Ink + Indigo** if:
- The buyer is a partner / CFO at a traditional advisory, accounting, or law firm.
- "Aethos, for professional services" needs to be explicit on the logo — outreach decks, cold emails, invoice headers — because the audience won't read body copy.
- You're willing to invest a bit more typographic care for a more authoritative register.
- You're OK with a weaker favicon (monogram fallback) in exchange for a stronger desktop / print presence.

**Pick Theme 3 — Carbon + Amber** if:
- The buyer is a boutique firm that charges premium rates and markets on craft / considered work.
- You want the brand to be the differentiator — to look unlike every other dashboard the buyer has seen.
- You have conviction that warm, editorial design will resonate, and you're OK with the higher variance.
- This is the one to pick if you want the brand to do marketing work for you, not just identify the product.

---

## Chitra's recommendation

**Theme 1 — Slate + Emerald** for v1.

Rationale: ship-speed matters in Week 1, the rotated-square mark is the most favicon-safe of the three, and the emerald accent doubling as the success / payment-received / approval semantic is a coherence win the other themes give up. Themes 2 and 3 are real options for a v1.1 brand refresh after we have design-partner feedback on what resonates — they are not throwaways.

If the founder leans toward a more distinctive personality from day one and accepts the higher execution cost, **Theme 3 — Carbon + Amber** is the contrarian pick that maximises brand recall. Theme 2 is the safe-conservative-buyer pick; I would only choose it if the first three design partners are all senior advisory / accounting firms.

---

## What's in each theme directory

```
theme-N-<name>/
  lockup.svg                  # primary mark — text + iconography, hand-coded SVG
  palette.md                  # full colour spec with hex / Tailwind / WCAG contrast notes
  tailwind.config.partial.js  # drop-in extension for frontend/tailwind.config.js
  mockup.html                 # standalone preview — copilot, inbox, invoice list, signup hero
  notes.md                    # mood / buyer / trade-off pitch (3-4 sentences)
```

After selection, a follow-up task assigned to Rupa will wire the chosen `tailwind.config.partial.js` into `frontend/tailwind.config.js`, update `DESIGN_SYSTEM.md` token tables to match, and update component styles where they reference accent colours.
