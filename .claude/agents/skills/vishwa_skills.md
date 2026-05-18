# Vishwa — CPTO Delegation & Review Skills

## Skill: Feature Decomposition

When receiving a feature request, decompose using this matrix:

| Layer | Agent | Ticket Title Pattern | Priority |
|-------|-------|---------------------|----------|
| Requirements | Netra | `[Netra] Define requirements for X` | HIGH |
| Architecture | Vastu | `[Vastu] Design architecture for X` | HIGH |
| UI Design | Chitra | `[Chitra] Design UI for X` | MEDIUM |
| Backend | Karya | `[Karya] Implement backend for X` | HIGH |
| Frontend | Rupa | `[Rupa] Implement frontend for X` | MEDIUM |
| Tests | Aksha | `[Aksha] Test X` | HIGH |
| Infrastructure | Sthira | `[Sthira] Deploy/configure X` | LOW |
| **Security Review** | **Prahari** | `[Prahari] Security review for X` | **HIGH** |

**Mandatory Prahari trigger**: Any feature that touches auth, payments, RLS, agent tools, external integrations, or JWT handling MUST have a Prahari security review before `status:in-review`.

### Decomposition Decision Tree
```
Is this a bug fix?
  → Yes: Assign directly to Karya (backend) or Rupa (frontend)
  → No: Is this a simple UI change?
    → Yes: Chitra (design) → Rupa (implement) → Aksha (test)
    → No: Is this a backend-only change?
      → Yes: Karya (implement) → Aksha (test)
      → No: Full pipeline: Netra → Vastu → Chitra → Karya+Rupa → Aksha → Sthira
```

## Skill: Code Review Checklist

When reviewing agent output before marking COMPLETED:

### Backend (Karya's work)
- [ ] Uses `Decimal` for all money values
- [ ] All queries are tenant-scoped
- [ ] Journal entries balance (debits = credits)
- [ ] Period lock is enforced
- [ ] No PII sent to external LLM APIs
- [ ] Error handling and graceful degradation present
- [ ] Type hints on all functions
- [ ] **Package verification done** — for any new third-party import, confirm the package is installed in `.venv` and the module/class/method actually exists at that path. `from pkg.submodule import X` written from memory without verification is a common failure mode (e.g., `langfuse.opentelemetry` not existing in v4). Check: did Karya run `.venv/bin/python -c "from <pkg> import <X>; print('OK')"` before shipping?

### Frontend (Rupa's work)
- [ ] Works in both light and dark themes
- [ ] Uses design system tokens
- [ ] Standalone components (no NgModules)
- [ ] Lazy-loaded routes
- [ ] Accessible (ARIA labels, keyboard nav)
- [ ] No hardcoded URLs or magic numbers

### Tests (Aksha's work)
- [ ] Covers happy path and edge cases
- [ ] Uses Decimal for money tests
- [ ] Tests tenant isolation
- [ ] No flaky tests
- [ ] Grounded in actual codebase (not generic)

### Security (Prahari's work — required for auth/payment/agent features)
- [ ] OWASP Top 10 checklist completed
- [ ] No critical or high findings open
- [ ] Tenant isolation verified
- [ ] No secrets in code or logs
- [ ] Rate limiting on sensitive endpoints

## Skill: Sprint Health Assessment

When assessing team health, query:
```sql
SELECT status, COUNT(*) as count FROM tickets GROUP BY status;
SELECT assignee, COUNT(*) as count FROM tickets WHERE status='ASSIGNED' GROUP BY assignee;
SELECT assignee, COUNT(*) as count FROM tickets WHERE status='IN_PROGRESS' GROUP BY assignee;
```

Flag issues:
- Agent with > 5 ASSIGNED tickets = overloaded
- Tickets IN_PROGRESS for > 2 days = potentially blocked
- IN_QA tickets without Aksha assignment = QA bottleneck
