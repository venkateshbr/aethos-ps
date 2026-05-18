# Netra — Product Management Skills

## Skill: User Story Format

### Template
```
**US-[ID]: [Title]**
As a [role], I want [action], so that [outcome].

**Acceptance Criteria:**
- Given [precondition], when [action], then [expected result]
- Given [precondition], when [edge case], then [graceful handling]

**Agent Interaction:**
- Agent autonomy level: L[0-3]
- HITL checkpoint: [Yes/No] — at which step?
- Fallback behavior: [What happens if agent is unavailable?]

**Priority:** Must/Should/Could/Won't
**Estimated Effort:** S/M/L/XL
```

### Example
```
**US-042: Invoice Auto-Classification**
As an SME bookkeeper, I want incoming invoices to be automatically classified 
to the correct expense account, so that I can save time on data entry.

**Acceptance Criteria:**
- Given a new invoice upload, when the AI agent processes it, then the expense 
  account is classified with ≥85% confidence
- Given a classification with <85% confidence, when the agent flags it, then 
  a HITL dialog asks the user to confirm or correct
- Given the LLM API is down, when an invoice is uploaded, then the invoice is 
  saved with status "pending_classification" and the user is notified

**Agent Interaction:**
- Agent autonomy level: L2 (act + notify)
- HITL checkpoint: Yes — when confidence < 85%
- Fallback behavior: Save as "pending_classification", notify user

**Priority:** Must
**Estimated Effort:** L
```

## Skill: PRD Section Template

```markdown
## Feature: [Name]

### Problem Statement
[Clear description of the user pain point]

### User Personas
- Primary: [SME bookkeeper / Business owner]
- Secondary: [Accountant / Auditor]

### Requirements
| ID | Requirement | Priority | Agent-Assisted? |
|----|-------------|----------|-----------------|
| R-01 | ... | Must | Yes (L2) |
| R-02 | ... | Should | No |

### Success Metrics
- [Metric 1]: [Target value]
- [Metric 2]: [Target value]

### Out of Scope
- [Things explicitly NOT included]
```

## Skill: Competitive Analysis Framework

When evaluating features against competitors:

| Criterion | Aethos | QuickBooks | Xero | FreshBooks |
|-----------|--------|------------|------|------------|
| Agent autonomy | ✅ L0-L3 | ❌ | ❌ | ❌ |
| HITL checkpoints | ✅ | ❌ | ❌ | ❌ |
| Multi-tenant | ✅ RLS | ✅ | ✅ | ✅ |
| Open API | ✅ | ✅ | ✅ | ✅ |
| GAAP compliance | ✅ | ✅ | ✅ | ⚠️ |

Always position Aethos differentiation on: **AI-first agent autonomy with progressive trust building.**
