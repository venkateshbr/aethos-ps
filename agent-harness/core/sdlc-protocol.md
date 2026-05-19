# SDLC Protocol

This protocol is the canonical way of working for agent-assisted projects.

## Mandatory First Step

Before changing tracked files:

1. Act as Vishwa if no role is specified.
2. Sync the canonical issue tracker.
3. Find or create the relevant issue.
4. Confirm issue type, priority, owner role, and status.
5. Move the issue to `in-progress`.
6. Do the work.
7. Hand off to QA/review rather than self-closing.

## Role Order

```text
Netra -> Vastu -> Chitra -> Karya/Rupa -> Vastu -> Aksha -> Sthira -> Vishwa
```

Shortcuts are allowed for small changes:

- Bug fix: Vishwa -> Karya/Rupa -> Aksha -> Vishwa.
- UI-only: Chitra -> Rupa -> Aksha -> Vishwa.
- Backend-only: Karya -> Aksha -> Vishwa.
- Docs-only: Vishwa -> Dhruva -> Vishwa.
- Infra-only: Sthira -> Aksha -> Vishwa.

Prahari is mandatory before review for auth, authorization, tenant isolation,
agent tools, external integrations, secrets, payment flows, webhooks, and other
security-sensitive work.

## Issue Lifecycle

```text
triage -> assigned -> in-progress -> in-qa -> in-review -> closed
```

Rules:

- Vishwa owns triage, decomposition, and final closure.
- Aksha owns QA sign-off and promotion to review.
- Prahari owns security sign-off when triggered.
- Agents do not close their own issues.

## Definition Of Done

All work:

- Acceptance criteria are met.
- Required role reviews are complete.
- No secrets or raw PII are committed.
- CI/developer checks pass or failures are documented.
- Real acceptance evidence exists for touched product workflows.
- User-facing changes are documented where needed.

Backend:

- Router -> Service -> Repository pattern or project equivalent.
- Queries are tenant/user scoped where applicable.
- Money uses exact decimal types.
- Type hints on public functions.
- External APIs/packages were verified against current docs or installed code.

Frontend:

- Uses the project's design system.
- Accessible interactive controls.
- Responsive states verified for relevant viewports.
- Avoids unrelated visual rewrites.

## Pull Request Protocol

- Branch names include type and issue number, for example
  `feat/123-subscription-webhook`.
- PR title follows conventional commits when possible.
- PR body includes `Fixes #<issue>`.
- Include verification evidence and residual risk.
- Squash-merge to main unless the project declares otherwise.

