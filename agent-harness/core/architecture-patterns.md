# Architecture Patterns

## Layering

Prefer explicit layers:

```text
Route / Controller -> Service -> Repository / Gateway -> Database or External API
```

- Routes validate transport concerns and call services.
- Services contain business logic.
- Repositories contain persistence details.
- Gateways wrap external APIs.

## ADRs

Record material architecture decisions as ADRs:

- Context
- Decision
- Consequences
- Alternatives considered
- Security and testing implications

## Data Contracts

- Define request/response models at boundaries.
- Keep internal persistence shapes separate from API contracts.
- Use migration files for schema changes.
- Update docs and tests with contract changes.

## Frontend

- Use the project design system before inventing styles.
- Keep routes lazy-loaded where the framework supports it.
- Prefer accessible native controls and semantic HTML.
- Use design tokens instead of hardcoded colors.
- Verify important views in real browser sessions.

## Observability

- Health endpoints should expose status and version, not secrets.
- Integration failures should be visible in logs and admin health screens.
- Agent and external API calls should be traceable.

