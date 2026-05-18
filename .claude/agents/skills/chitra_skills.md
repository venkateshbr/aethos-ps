# Chitra — Design System Skills

## Skill: Component Design Spec Template

```markdown
## Component: [Name]

### Purpose
[One sentence: what does this component do?]

### Variants
- Default, Hover, Focused, Active, Disabled, Loading, Error

### Design Tokens
| Token | Light Mode | Dark Mode |
|-------|-----------|-----------|
| Background | `slate-50` | `slate-800` |
| Text | `slate-900` | `slate-50` |
| Border | `slate-200` | `slate-700` |
| Accent | `indigo-600` | `indigo-400` |

### Spacing
- Padding: `p-4` (16px)
- Gap: `gap-3` (12px)
- Border radius: `rounded-lg` (8px)

### Typography
- Heading: `text-lg font-semibold`
- Body: `text-sm font-normal`
- Caption: `text-xs text-slate-400`

### Accessibility
- Role: `[button|dialog|alert|etc.]`
- ARIA: `aria-label="[description]"`
- Keyboard: `Enter` to activate, `Escape` to dismiss
- Focus visible: `ring-2 ring-indigo-400`

### Interaction States
| State | Background | Border | Text |
|-------|-----------|--------|------|
| Default | `slate-800` | `slate-700` | `slate-50` |
| Hover | `slate-700` | `indigo-500` | `white` |
| Focus | `slate-800` | `indigo-400` | `slate-50` |
| Active | `slate-900` | `indigo-600` | `white` |
| Disabled | `slate-800/50` | `slate-700/50` | `slate-500` |

### Hand-off to Rupa
- [ ] Tokens defined in DESIGN_SYSTEM.md
- [ ] All states specified
- [ ] Responsive breakpoints noted
- [ ] Accessibility requirements clear
```

## Skill: WCAG 2.1 AA Quick Reference

### Color Contrast
- Normal text (< 18px): minimum 4.5:1 ratio
- Large text (≥ 18px or bold ≥ 14px): minimum 3:1 ratio
- UI components: minimum 3:1 ratio

### Our Dark Theme Contrast Ratios (pre-calculated)
| Combination | Ratio | Pass? |
|------------|-------|-------|
| `slate-50` on `slate-900` | 15.4:1 | ✅ AAA |
| `slate-300` on `slate-900` | 8.3:1 | ✅ AAA |
| `slate-400` on `slate-800` | 4.6:1 | ✅ AA |
| `indigo-400` on `slate-900` | 5.2:1 | ✅ AA |
| `amber-400` on `slate-900` | 8.9:1 | ✅ AAA |

### Focus Indicators
- All interactive elements MUST have visible focus ring
- Use: `focus:ring-2 focus:ring-indigo-400 focus:ring-offset-2 focus:ring-offset-slate-900`
- Never use `outline-none` without a visible alternative

## Skill: Agent UI Patterns

### Confidence Meter
- 90-100%: `emerald-400` — "High confidence"
- 70-89%: `amber-400` — "Medium confidence — review recommended"
- 0-69%: `red-400` — "Low confidence — manual review required"

### HITL Dialog
- Always show: What the agent wants to do, confidence level, and reasoning
- Always offer: Approve, Reject, or Edit before approve
- Never auto-dismiss — require explicit user action
