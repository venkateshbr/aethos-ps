# Operating Principles

These principles are the default behavior for all agents and models using the
harness.

## Founder Request Flow

- Treat every unassigned request as Vishwa triage first.
- Clarify only when a reasonable assumption would create material risk.
- Once scope is clear, execute rather than only proposing.
- Keep the user informed with concise progress updates during long work.
- Preserve the user's work. Never revert unrelated changes.

## Repository First

- Read the repo before inventing patterns.
- Prefer existing architecture, helper APIs, design tokens, test utilities, and
  package managers.
- Keep edits scoped to the requested behavior.
- Use structured parsers/APIs where available.
- Add abstractions only when they remove real complexity or match a local pattern.

## Issue First

- No tracked code or documentation change starts without an issue or equivalent
  work item.
- GitHub Issues are recommended, but Jira, Linear, or another tracker can be
  substituted if the project declares it as canonical.
- The issue should contain scope, acceptance criteria, and required review gates.

## Safety First

- Never commit secrets, credentials, temporary passwords, tokens, or raw PII.
- Security-sensitive work triggers Prahari review.
- External integrations require package/API verification before coding.
- Agent actions that write to production data require a human-in-the-loop gate.

## Evidence Over Assertions

- Passing type checks and unit tests are developer checks.
- Product acceptance requires real API and real UI evidence where applicable.
- State what was verified, what was not verified, and any remaining risk.

