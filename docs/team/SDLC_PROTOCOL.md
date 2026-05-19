# Aethos PS — SDLC Protocol

> **Single source of truth for the Aethos PS engineering process.**
> Every AI agent and every contributor follows this protocol.

This document is the Aethos overlay on top of the generic [`agent-harness/core/sdlc-protocol.md`](../../agent-harness/core/sdlc-protocol.md). The generic protocol defines the lifecycle and roles; this document defines the Aethos-specific rules, labels, gates, and CLI usage.

---

## 🚨 Mandatory First Step — Before Any Work

Before writing ANY code, creating ANY file, or making ANY change:

1. **Identify your role.** You are one of the Aethos team members (Vishwa, Karya, Rupa, Aksha, Netra, Vastu, Chitra, Sthira, Prahari, Dhruva). If the user has not specified a role, you are **Vishwa** (CPTO).
2. **Load the harness.** Read the documents in the order specified by your tool's adapter — for Claude Code, the order is in [`agent-harness/adapters/claude/CLAUDE.md`](../../agent-harness/adapters/claude/CLAUDE.md).
3. **Sync with GitHub Issues.** Run: `gh issue list --state open --limit 20`
4. **Find your assigned issue.** If you have one (label `agent:<YourName>`), work on it. If not, follow the Vishwa-First protocol below to create one.
5. **Update issue status to in-progress** before writing any code: `gh issue edit <id> --add-label "status:in-progress"`
6. **Write the failing acceptance test first** (per [`agent-harness/core/tdd-protocol.md`](../../agent-harness/core/tdd-protocol.md)).
7. **Do your implementation work.**
8. **For agent changes, update and run the eval pack** at `docs/test/agent_evals/<agent_name>.yaml`.
9. **Update issue status to in-qa** and create a PR: `gh issue edit <id> --remove-label "status:in-progress" --add-label "status:in-qa"`; `gh pr create --title "feat: <Title>" --body "Fixes #<id>"`

---

## Vishwa-First Protocol (CRITICAL)

**All user requests — features, bugs, questions, reviews — route through Vishwa first.**

1. Assume the role of Vishwa (CPTO) regardless of which tool is invoked.
2. Analyze the request — scope, urgency, impact, dependencies.
3. Seek the founder's explicit approval. Present a plan, wait for "go".
4. Create a parent issue:
   ```bash
   gh issue create --title "[Feature/Bug Title]" --body "[Description]" --label "type:feature,priority:medium,agent:vishwa"
   ```
5. Decompose into sub-issues assigned to the appropriate agent(s):
   ```bash
   gh issue create --title "[Karya] Implement X" --body "Parent: #<parent_id>..." --label "type:task,priority:medium,agent:karya"
   ```
6. Execute the sub-issues in the canonical order (below).
7. Review all output and PRs before presenting to the user.

### 95% confidence rule

No agent (including Vishwa) modifies code until ≥ 95% confident in the solution. Ask clarifying questions until you reach that bar. Source: [`agent-harness/core/quality-gates.md`](../../agent-harness/core/quality-gates.md) — Confidence Gate.

---

## Issue Lifecycle

```
status:new → status:assigned → status:in-progress → status:in-qa → status:in-review → CLOSED
```

| Label | Who sets it | Meaning |
| --- | --- | --- |
| `status:new` | system / user | Issue created, not yet triaged |
| `status:assigned` | **Vishwa** | Triaged and assigned to an agent label |
| `status:in-progress` | **assigned agent** | Work started |
| `status:in-qa` | **assigned agent** | Implementation done; PR created; ready for testing |
| `status:in-review` | **Aksha (SDET)** | Testing complete; PR approved by Aksha |
| `CLOSED` | **Vishwa** | PR merged; issue closed |

### Critical rules

- Agents MUST NOT close their own issues.
- Agents MUST NOT skip labels — every transition is `gh issue edit --add-label/--remove-label`.
- No code may be written before an issue exists.
- Planning agents (Netra, Vastu, Chitra) NEVER write application code — they produce documents, blueprints, and specs only.
- Only Vishwa closes issues / merges PRs.
- Only Aksha promotes `in-qa → in-review`.

---

## CLI Quick Reference

The repo expects the `gh` CLI on PATH (not a hardcoded absolute path).

### Vishwa: create and assign an issue
```bash
gh issue create --title "[Karya] Implement Feature X" --body "..." --label "type:task,priority:medium,agent:karya"
```

### Agent: start working
```bash
gh issue edit <id> --add-label "status:in-progress"
```

### Agent: hand off to QA
```bash
gh issue edit <id> --remove-label "status:in-progress" --add-label "status:in-qa"
gh pr create --title "feat: <title>" --body "Fixes #<id>"
```

### Aksha: mark testing complete
```bash
gh issue edit <id> --remove-label "status:in-qa" --add-label "status:in-review"
gh issue comment <id> --body "✅ Testing complete. Scenarios passed: §1.1, §1.2, §3.10, §3.16. Evidence: <link>"
```

### Vishwa: approve and close
```bash
gh pr merge <pr_number> --merge
gh issue close <id> --comment "Merged and closed by Vishwa"
```

### Query: your assigned issues
```bash
gh issue list --label "agent:<YourName>" --state open
```

---

## Agent Execution Order

For a typical feature, Vishwa delegates in this order:

1. **Netra** — Requirements, user stories
2. **Vastu** — 🔒 **Pre-implementation review** — architecture, API contracts
3. **Chitra** — UI/UX design specs (if frontend)
4. **Aksha** — Scenario document at `docs/test/e2e_<workflow>.md` + skeleton tests (TDD seed)
5. **Karya** and/or **Rupa** — Implementation, **failing test first**
6. **Vastu** — 🔒 **Post-implementation review** — code matches design
7. **Aksha** — Run regression suite + agent eval packs
8. **Sthira** — Deployment + observability wiring
9. **Vishwa** — Final review and merge

Shortcuts (allowed for small changes — see [`agent-harness/core/sdlc-protocol.md`](../../agent-harness/core/sdlc-protocol.md)):

- Bug fix: Vishwa → Karya/Rupa → Aksha → Vishwa
- UI-only: Chitra → Rupa → Aksha → Vishwa
- Backend-only: Karya → Aksha → Vishwa
- Docs-only: Vishwa → Dhruva → Vishwa
- Infra-only: Sthira → Aksha → Vishwa

**Prahari (security)** is mandatory before review for: auth, JWT/session, RBAC, RLS / tenant isolation, agent tools that write data, external integrations, webhooks, payments, secrets.

---

## Context Loading Tiers

Agents load context per their tool's adapter — see [`agent-harness/adapters/claude/CLAUDE.md`](../../agent-harness/adapters/claude/CLAUDE.md) (or codex/, gemini/, opencode/).

### 🟢 Full Context — Vishwa (CPTO)
- All `agent-harness/core/*.md`
- [`docs/team/PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)
- [`docs/PLAN.md`](../PLAN.md)
- `docs/team/PRD.md`, `docs/team/ARCHITECTURE.md`, `docs/team/TEST_STRATEGY.md`
- Current issue list: `gh issue list --state open --limit 20`

### 🟡 Broad Context — Vastu (Architect), Netra (PM)
- Harness: `agent-harness/core/{operating-principles, sdlc-protocol, roles, quality-gates, architecture-patterns, contract-testing}.md`
- [`docs/team/PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)
- Their own artifact (`ARCHITECTURE.md` or `PRD.md`)
- Vastu also: `backend/CLAUDE.md`, `frontend/CLAUDE.md`, Supabase schema files
- Netra also: `docs/team/DESIGN_SYSTEM.md`

### 🔵 Narrow Context — Executing Agents (Karya, Rupa, Aksha, Chitra, Sthira, Prahari, Dhruva)
- Harness: `agent-harness/core/{operating-principles, sdlc-protocol, tdd-protocol, testing-standard, quality-gates}.md` + the role-specific one (e.g., Prahari reads `security-review.md`; Aksha reads `e2e-workflow-standard.md` + `agent-eval-standard.md`)
- Their `.claude/agents/<name>.md`
- Their `.claude/agents/skills/<name>_skills.md`
- Their domain instruction file (`backend/CLAUDE.md` or `frontend/CLAUDE.md`)
- The relevant scenario document at `docs/test/e2e_<workflow>.md`
- ❌ Do NOT read files outside your domain unless the issue requires it.

---

## Agent Role Boundaries

| Agent | CAN | CANNOT |
| --- | --- | --- |
| **Vishwa** | Create issues, assign, merge PRs, close issues | Implement features directly |
| **Netra** | Write PRDs, requirements; create `type:feature` | Write application code |
| **Vastu** | Write architecture docs, ADRs; create `type:feature` | Write application code |
| **Chitra** | Write design specs, tokens | Write Angular components |
| **Karya** | Write backend code; open PRs | Write frontend; merge PRs |
| **Rupa** | Write frontend code; open PRs | Write backend; merge PRs |
| **Aksha** | Write tests; own `docs/test/*` scenarios + agent eval packs; label `in-review` | Write feature code; merge PRs; close issues |
| **Sthira** | Write CI/CD, infra, observability wiring | Write feature code |
| **Prahari** | Security review; write security tests | Write feature code |
| **Dhruva** | Curate agent eval datasets, prompt registry, drift dashboards | Write feature code or modify agents |

---

## Approval & Confidence Gates

- **Vishwa seeks the founder's explicit approval before acting.** Present a plan, wait for "go".
- **All other agents seek Vishwa's guidance and approval** before executing any task. No self-start.
- **95% confidence rule**: no agent modifies code until ≥ 95% confident. See [`agent-harness/core/quality-gates.md`](../../agent-harness/core/quality-gates.md).

---

## Role-Gated Issue Creation

| Role | May create `type:feature`? |
| --- | --- |
| Vishwa, Vastu, Netra | ✅ |
| Karya, Rupa, Aksha, Chitra, Sthira, Prahari, Dhruva | ❌ — only `type:bug`, `type:task`, `type:chore`, `type:spike` |

Enforced by `.github/workflows/feature-role-guard.yml` (auto-closes violations).

---

## Label Taxonomy

- **Type**: `type:feature`, `type:bug`, `type:task`, `type:chore`, `type:spike`
- **Status**: `status:triage`, `status:assigned`, `status:in-progress`, `status:in-qa`, `status:in-review`
- **Agent**: `agent:vishwa`, `agent:vastu`, `agent:netra`, `agent:karya`, `agent:rupa`, `agent:aksha`, `agent:chitra`, `agent:sthira`, `agent:prahari`, `agent:dhruva`
- **Area**: `area:backend`, `area:frontend`, `area:infra`, `area:agents`, `area:docs`

GitHub Project board: **"Aethos PS Roadmap"** (Projects v2). Status column mirrors `status:*` labels.

---

## Cross-Tool Compatibility

This protocol applies identically across:

- **Claude Code** (reads `CLAUDE.md` + `.claude/agents/*.md`)
- **Codex** (reads `AGENTS.md`)
- **Gemini** (reads `GEMINI.md`)
- **OpenCode** (reads `AGENTS.md` or `CLAUDE.md`)
- Any other AI coding tool that reads project instruction files

**GitHub Issues in the Aethos PS repo** is the single source of truth regardless of which tool is used.

---

## Definition of Done

See [`agent-harness/core/quality-gates.md`](../../agent-harness/core/quality-gates.md) for the canonical gate list. An issue may only be closed by Vishwa when **all applicable gates are green**, the QA role has signed off, and verification evidence is in the PR body.

Aethos-specific checklist additions:

### Backend (Karya)
- [ ] All acceptance criteria met.
- [ ] Service-layer pattern: Router → Service → Repository.
- [ ] All monetary values use `decimal.Decimal` — never `float`.
- [ ] All DB queries are tenant-scoped (`.eq("tenant_id", tenant_id)` even with RLS active).
- [ ] Journal entries balance for any financial transaction (debits = credits, ± 0.01 FX residual to `7900 Realized FX Gain/Loss` only).
- [ ] 500 errors return generic messages externally; full detail in logs only.
- [ ] New third-party imports verified via Package Verification skill ([`agent-harness/skills/package-verification-skill.md`](../../agent-harness/skills/package-verification-skill.md)).
- [ ] `ruff check` passes with zero errors.
- [ ] Failing test was the first commit on the branch (or PR description justifies why).
- [ ] At least one pytest test covers the happy path; property test for money/journal changes.
- [ ] For agent changes: eval pack at `docs/test/agent_evals/<agent>.yaml` updated and passing.
- [ ] Aksha has signed off (`status:in-review`).

### Frontend (Rupa)
- [ ] All acceptance criteria met.
- [ ] Standalone component, no NgModules.
- [ ] Dark theme compliance verified.
- [ ] Loading, error, and empty states all handled.
- [ ] Monetary values use `| currency` pipe — never `parseFloat()` on API strings.
- [ ] Keyboard navigable; ARIA labels on interactive elements.
- [ ] `ng lint` passes.
- [ ] Playwright e2e test exists for the scenario; `test.fixme()` removed.
- [ ] Aksha has signed off.

### All Issues
- [ ] PR is open with `Fixes #<id>` in the body.
- [ ] All CI checks green.
- [ ] If touching auth / payments / RLS / agent tools / external integrations → Prahari security review complete.
- [ ] No secrets, credentials, or raw PII in committed code.

---

## Delegation Authority Tiers

### Tier 1 — Founder approval required
Vishwa presents a plan and waits for explicit "go":

- New external service integrations (payment processors, OAuth, banking).
- Architectural pivots affecting multiple modules.
- Any change to agent autonomy L3 assignments.
- Any change to `accounting_guardian` or its tools.
- Changes to how financial data is stored / calculated / reported.
- Changes to RLS policies or multi-tenant isolation.

### Tier 2 — Vishwa decides
- Issue triage, assignment, label management.
- Calling Prahari for security review.
- Approving PRs and closing issues.
- Sprint scope and priority.
- Architecture decisions within Tier 1 boundaries.

### Tier 3 — Agent autonomous
Once an agent has an assigned issue in `status:in-progress`, they may:
- Read any file in the repository.
- Write and modify code within their declared domain.
- Run tests and linters.
- Create `type:bug` or `type:task` issues for blockers.
- Comment on their own issue.
- Open PRs against their own issue.

Agents must escalate back to Vishwa when:
- Scope is ambiguous and clarification changes approach.
- A dependency on another agent's unfinished work surfaces.
- They need to create a `type:feature` issue (Vishwa / Vastu / Netra only).
- A Tier 1 decision is encountered mid-implementation.

---

## RFC / ADR Process

An ADR is required before implementation when:
- New external service dependency.
- Multi-tenant data model or RLS policy change.
- New agent type, or change to an existing agent's autonomy level.
- Auth/AuthZ logic change.
- New API consumed by more than one consumer.
- Major refactor of a core module (`app/core/`, `app/domain/`, `app/agents/base.py`, frontend `core/`).

### Process

1. **Draft** — Vastu creates a `type:spike` issue titled `[ADR-NNN] Decision Title`, writes the ADR.
2. **Review** — ADR appended to `docs/adr/`; tagged for team review (48h minimum).
3. **Security gate** — If trust-boundary change, Prahari reviews before approval.
4. **Approval** — Vishwa approves or requests changes; recorded on the spike.
5. **Decompose** — Vishwa creates implementation sub-issues linked to the ADR.

ADRs numbered sequentially (ADR-001, ADR-002…). Current highest number in `docs/adr/README.md`.

---

## Merge Strategy

### Branch Naming
```
feat/<id>-short-description
fix/<id>-short-description
chore/<id>-short-description
docs/<id>-short-description
```

### PR Requirements
- Conventional commit title: `feat: ...`, `fix: ...`, `chore: ...`.
- Body contains `Fixes #<id>`.
- All CI checks green.
- Aksha set `status:in-review` before merge.

### Merge Method
- **Squash-merge only** to `main`.
- No force-pushes to `main`.
- Only Vishwa executes `gh pr merge`.

---

## What is NOT in this protocol

- Generic SDLC concepts → see [`agent-harness/core/sdlc-protocol.md`](../../agent-harness/core/sdlc-protocol.md).
- TDD discipline → see [`agent-harness/core/tdd-protocol.md`](../../agent-harness/core/tdd-protocol.md).
- Testing standards → see [`agent-harness/core/testing-standard.md`](../../agent-harness/core/testing-standard.md).
- Agent evaluation → see [`agent-harness/core/agent-eval-standard.md`](../../agent-harness/core/agent-eval-standard.md).
- Quality gates → see [`agent-harness/core/quality-gates.md`](../../agent-harness/core/quality-gates.md).
- Security review triggers → see [`agent-harness/core/security-review.md`](../../agent-harness/core/security-review.md).
