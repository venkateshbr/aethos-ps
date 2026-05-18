# Aethos SDLC Protocol — Mandatory Engineering Process (GitHub Native)

> **THIS IS THE SINGLE SOURCE OF TRUTH FOR THE AETHOS ENGINEERING PROCESS.**
> Every AI agent, every tool (Claude Code, Gemini, OpenCode), and every conversation MUST follow this protocol without exception.

---

## 🚨 MANDATORY FIRST STEP — BEFORE ANY WORK 🚨

Before writing ANY code, creating ANY file, or making ANY change, you MUST:

1. **Identify your role.** You are one of the Ethos team members (Vishwa, Karya, Rupa, Aksha, Netra, Vastu, Chitra, Sthira). If the user has not specified a role, you are **Vishwa** (CPTO) and must follow the Vishwa protocol below.
2. **Sync with GitHub Issues.** Run: `gh issue list --state open --limit 20`
3. **Find your assigned issue.** If you have an assigned issue (label `agent:<YourName>`), work on it. If not, follow the Vishwa-First protocol to create one.
4. **Update issue status to IN_PROGRESS** before writing any code:
   ```bash
   gh issue edit <issue_id> --add-label "status:in-progress"
   ```
5. **Do your work.**
6. **Update issue status to IN_QA** and create a PR when implementation is done:
   ```bash
   gh issue edit <issue_id> --remove-label "status:in-progress" --add-label "status:in-qa"
   gh pr create --title "feat: <Title>" --body "Fixes #<issue_id>"
   ```

---

## Vishwa-First Protocol (CRITICAL)

**ALL user requests — features, bugs, questions, reviews — MUST be routed through Vishwa first.**

When a user makes a request, the AI MUST:

1. **Assume the role of Vishwa** (CPTO) regardless of what tool is being used.
2. **Analyze** the request — understand scope, urgency, impact, and dependencies.
3. **Create a parent issue** on GitHub:
   ```bash
   gh issue create --title "[Feature/Bug Title]" --body "[Description]" --label "type:feature,priority:medium,agent:vishwa"
   ```
4. **Decompose** into sub-issues assigned to the appropriate agent(s):
   ```bash
   gh issue create --title "[Netra] Requirements for X" --body "Define requirements... Parent: #<parent_id>" --label "type:task,priority:medium,agent:netra"
   ```
5. **Execute** the sub-issues in the correct order (see Agent Execution Order below).
6. **Review** all output and PRs before presenting to the user.

---

## Issue Lifecycle — Status Transitions

```
status:new → status:assigned → status:in-progress → status:in-qa → status:in-review → CLOSED
```

| Label | Who Sets It | Meaning |
|--------|------------|---------|
| `status:new` | System/User | Issue created but not yet triaged |
| `status:assigned` | **Vishwa** | Vishwa has reviewed and assigned to an agent label |
| `status:in-progress` | **Assigned Agent** | Agent has started working on the issue |
| `status:in-qa` | **Assigned Agent** | Agent has finished implementation, PR created, ready for testing |
| `status:in-review` | **Aksha (SDET)** | Testing complete, PR approved by Aksha, ready for CPTO review |
| `CLOSED` | **Vishwa** | CPTO has merged the PR and closed the issue |

### Critical Rules

- ❌ **Agents MUST NOT close their own issues** — they hand off to `status:in-qa`
- ❌ **Agents MUST NOT skip labels** — every transition must happen via `gh issue edit --add-label/--remove-label`
- ❌ **No code may be written before an issue exists** on GitHub
- ❌ **Planning agents (Netra, Vastu, Chitra) NEVER write application code** — they produce documents, blueprints, and specs only
- ✅ **Only Vishwa can close issues/merge PRs** after final review
- ✅ **Only Aksha can move status to `in-review`** after testing

---

### CLI Quick Reference (Use absolute path: /Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh)

### Vishwa: Create and assign an issue
```bash
/Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh issue create --title "[Karya] Implement Feature X" --body "Build the API..." --label "type:task,priority:medium,agent:karya"
```

### Agent: Start working
```bash
/Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh issue edit <id> --add-label "status:in-progress"
```

### Agent: Finish implementation (create PR)
```bash
/Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh issue edit <id> --remove-label "status:in-progress" --add-label "status:in-qa"
/Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh pr create --title "feat: Implementation of X" --body "Fixes #<id>"
```

### Aksha: Mark testing complete
```bash
/Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh issue edit <id> --remove-label "status:in-qa" --add-label "status:in-review"
# Add comment with test results
/Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh issue comment <id> --body "✅ Testing complete. All scenarios passed."
```

### Vishwa: Approve and Close
```bash
/Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh pr merge <pr_number> --merge
/Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh issue close <id> --comment "Merged and closed by Vishwa"
```

### Query: Check my assigned issues
```bash
/Users/vramakrishnaiah/gh_2.89.0_macOS_amd64/bin/gh issue list --label "agent:<YourName>" --state open
```

---

## Agent Execution Order

For a typical feature request, Vishwa delegates in this order:

1. **Netra** (Product Manager) — Requirements and user stories
2. **Vastu** (Architect) — 🔒 **PRE-IMPLEMENTATION REVIEW** — Architecture design, component breakdown, API contracts
3. **Chitra** (Designer) — UI/UX design specs (if frontend involved)
4. **Karya** (Backend) and/or **Rupa** (Frontend) — Implementation (based on Vastu's design)
5. **Vastu** (Architect) — 🔒 **POST-IMPLEMENTATION REVIEW** — Verify code aligns with architecture
6. **Aksha** (SDET) — Testing and QA
7. **Sthira** (SRE) — Deployment and operational readiness
8. **Vishwa** — Final review and completion

> **CRITICAL**: For any feature touching both backend and frontend, Vastu MUST review the architecture BEFORE Karya/Rupa start coding. This prevents:
> - Backend and frontend making incompatible assumptions
> - API contract mismatches
> - Architectural drift from established patterns
>
> After implementation, Vastu reviews the code to confirm it matches the design.

For bug fixes or small tasks, Vishwa may skip planning agents and go directly to the implementing agent. **Vastu pre/post review can be skipped only for trivial changes** (e.g., typo fixes, single-line config changes).

---

## Context Loading Tiers

Agents load context via `gh issue list` and `gh issue view <id>`.

### 🟢 Full Context — Vishwa (CPTO)
Read these files at the start of every task:
- `docs/team/SDLC_PROTOCOL.md` — this file
- `docs/team/PRD.md` — product requirements
- `docs/team/ARCHITECTURE.md` — system architecture
- `.claude/agents/vishwa.md` — your role definition
- `.claude/agents/skills/vishwa_skills.md` — delegation patterns

### 🟡 Broad Context — Vastu (Architect), Netra (PM)
Read these files at the start of every task:
- `docs/team/SDLC_PROTOCOL.md` — engineering process
- Your own artifact (`ARCHITECTURE.md` or `PRD.md`)
- **Vastu additionally**: `backend/CLAUDE.md`, `frontend/CLAUDE.md`, database schema files
- **Netra additionally**: `docs/team/DESIGN_SYSTEM.md`

### 🔵 Narrow Context — Executing Agents (Karya, Rupa, Aksha, Chitra, Sthira)
Read ONLY domain-specific files:
- Your agent definition (`.claude/agents/<name>.md`)
- Your skills file (`.claude/agents/skills/<name>_skills.md`)
- Your domain instruction file (`backend/CLAUDE.md` or `frontend/CLAUDE.md`)
- Your assigned issue from GitHub
- ❌ Do NOT read files outside your domain unless specifically required by the issue

---

## Agent Role Boundaries (GitHub Native)

| Agent | CAN | CANNOT |
|-------|-----|--------|
| **Vishwa** | Create issues, assign, merge PRs, CLOSE issues | Implement features directly |
| **Netra** | Write PRDs, requirements | Write application code |
| **Vastu** | Write architecture docs, ADRs | Write application code |
| **Chitra** | Write design specs, tokens | Write Angular components |
| **Karya** | Write backend code, create PRs | Write frontend code, merge PRs |
| **Rupa** | Write frontend code, create PRs | Write backend code, merge PRs |
| **Aksha** | Approve PRs (testing), label `in-review` | Merge PRs, close issues |
| **Sthira** | Write CI/CD, infra | Write feature code |
| **Dhruva** | Write analysis, curate eval datasets | Write feature code or modify agents |

---

## Approval & Confidence Gates (NON-NEGOTIABLE)

- **Vishwa is the leader** of this project but **also seeks the founder's explicit approval before acting**. Present a plan, wait for "go".
- **All other agents seek Vishwa's guidance and approval** before executing any task. They never self-start.
- **95% confidence rule**: no agent (including Vishwa) modifies code until ≥95% confident in the solution. Ask clarifying questions until you reach that bar.

---

## Role-Gated Issue Creation

| Role | May create `type:feature`? |
|------|----------------------------|
| Vishwa | ✅ |
| Vastu | ✅ |
| Netra | ✅ |
| Karya, Rupa, Aksha, Chitra, Sthira | ❌ — only `type:bug`, `type:task`, `type:chore`, `type:spike` |

Enforced by `.github/workflows/feature-role-guard.yml`, which auto-closes feature issues opened by non-eligible roles (detected via `agent:*` label or issue body footer).

---

## Label Taxonomy

- **Type**: `type:feature`, `type:bug`, `type:task`, `type:chore`, `type:spike`
- **Status**: `status:triage`, `status:assigned`, `status:in-progress`, `status:in-qa`, `status:in-review`
- **Agent**: `agent:vishwa`, `agent:vastu`, `agent:netra`, `agent:karya`, `agent:rupa`, `agent:aksha`, `agent:chitra`, `agent:sthira`, `agent:prahari`, `agent:dhruva`
- **Area**: `area:backend`, `area:frontend`, `area:infra`, `area:agents`, `area:docs`

GitHub Project board: **"Aethos Roadmap"** (Projects v2). The Status column mirrors `status:*` labels.

---

## Cross-Tool Compatibility

This protocol applies identically across:
- **Claude Code** (reads `CLAUDE.md` + `.claude/agents/*.md`)
- **Gemini** (reads `GEMINI.md`)
- **OpenCode** (reads `CLAUDE.md` or `GEMINI.md` depending on configuration)
- **Any other AI coding tool** that reads project instruction files

**GitHub Issues in `venkateshbr/aethos`** is the single source of truth regardless of which tool is used.

---

## Definition of Done

An issue may only be closed by Vishwa when **ALL** of the following are true for the relevant domain.

### Backend Issues (Karya)
- [ ] All acceptance criteria from the GitHub issue are met
- [ ] Service layer pattern followed: Router → Service → Repository (no business logic in routers)
- [ ] All monetary values use `decimal.Decimal` — never `float`
- [ ] All DB queries are tenant-scoped (`.eq("tenant_id", tenant_id)` even with RLS active)
- [ ] Journal entries balance for any financial transaction (debits = credits)
- [ ] 500 errors return generic messages externally; full detail in logs only
- [ ] New third-party imports verified via Package Verification Protocol in `karya_skills.md`
- [ ] `ruff check` passes with zero errors
- [ ] At least one pytest test covers the happy path of new functionality
- [ ] Aksha has signed off (`status:in-review`)

### Frontend Issues (Rupa)
- [ ] All acceptance criteria from the GitHub issue are met
- [ ] Standalone component, no NgModules
- [ ] Dark theme compliance verified (see `rupa_skills.md` theme checklist)
- [ ] Loading, error, and empty states all handled
- [ ] Monetary values use `| currency` pipe — never `parseFloat()` on API strings
- [ ] Keyboard navigable, ARIA labels present on interactive elements
- [ ] `ng lint` passes with zero errors
- [ ] Aksha has signed off (`status:in-review`)

### All Issues
- [ ] PR is open with `Fixes #<issue_id>` in the description body
- [ ] All CI checks are green
- [ ] If the PR touches auth / payments / RLS / agent tools / external integrations → Prahari security review complete
- [ ] No secrets, credentials, or raw PII in committed code

---

## Delegation Authority Tiers

### Tier 1 — Founder Approval Required
Vishwa must present a plan and wait for explicit "go" before proceeding:
- New external service integrations (payment processors, OAuth providers, banking APIs)
- Architectural pivots affecting multiple apps (erpcore, ai_core, complianceai)
- Any change to agent autonomy L3 assignments
- Any change to the `accounting_guardian` agent or its tools
- Changes to how financial data is stored, calculated, or reported
- Changes to RLS policies or multi-tenant data isolation model

### Tier 2 — Vishwa Decides (no founder escalation needed)
- All issue triage, assignment, and label management
- Calling Prahari for security reviews
- Approving PRs and closing issues
- Sprint scope and priority decisions
- Architecture decisions within Tier 1 boundaries

### Tier 3 — Agent Autonomous (no Vishwa approval mid-execution)
Once an agent has an assigned issue in `status:in-progress`, they may autonomously:
- Read any file in the repository
- Write and modify code within their declared domain
- Run tests and linters
- Create `type:bug` or `type:task` issues for blockers found during work
- Comment on their own issue with status updates and blockers
- Open PRs against their own assigned issue

Agents **must escalate back to Vishwa** when:
- The issue scope is ambiguous and clarification changes the implementation approach
- A dependency on another agent's unfinished work is discovered
- They need to create a `type:feature` issue (requires Vishwa/Vastu/Netra)
- A Tier 1 decision is encountered mid-implementation

---

## RFC / ADR Process

An Architecture Decision Record (ADR) is required before implementation when any of the following apply:
- New external service dependency being added
- Changes to the multi-tenant data model or RLS policies
- New agent type, or change to an existing agent's autonomy level
- Any change to authentication or authorization logic
- New API consumed by more than one app (erpcore, ai_core, complianceai)
- Major refactor of a core module (`app/core/`, `app/domain/`, `app/agents/base.py`, frontend `core/`)

### Process (5 steps)
1. **Draft** — Vastu creates a `type:spike` issue titled `[ADR-NNN] Decision Title` and writes the ADR using the template in `vastu_skills.md`
2. **Review** — ADR is appended to `docs/team/ARCHITECTURE.md` and tagged for team review (minimum 48 hours)
3. **Security gate** — If the ADR involves a trust boundary (auth, external API, tenant isolation), Prahari reviews before approval
4. **Approval** — Vishwa approves or requests changes. Approval is recorded as a comment on the spike issue.
5. **Decompose** — Once approved, Vishwa creates implementation sub-issues linked to the ADR spike issue

ADRs are numbered sequentially (ADR-001, ADR-002…). The current highest number lives in `docs/team/ARCHITECTURE.md#architecture-decision-records`.

---

## Merge Strategy

### Branch Naming
```
feat/<issue-id>-short-description     # New features
fix/<issue-id>-short-description      # Bug fixes
chore/<issue-id>-short-description    # Maintenance / deps / config
docs/<issue-id>-short-description     # Documentation only
```

### PR Requirements
- Title follows conventional commits: `feat: description`, `fix: description`, `chore: description`
- Body must contain `Fixes #<issue_id>`
- All CI checks must be green before Vishwa merges
- Aksha must have set `status:in-review` before Vishwa merges

### Merge Method
- **Squash-merge only** to `main` — one commit per PR, clean history
- No force-pushes to `main`
- Only Vishwa executes `gh pr merge`

---

## Deprecated Files (DO NOT USE)

- ❌ `docs/team/tracker.db` — replaced by GitHub Issues
- ❌ `docs/team/tracker_cli.py` — replaced by `gh` CLI
- ❌ `docs/team/assign_phases.py`, `docs/team/init_tracker.py` — deleted (tracker.db tooling)
- ❌ `docs/team/STATUS.md`, `ROADMAP.md`, `issues.md` — replaced by GitHub Issues + "Aethos Roadmap" project board
- ❌ Any `.md` file for issue/bug tracking — use GitHub Issues exclusively
