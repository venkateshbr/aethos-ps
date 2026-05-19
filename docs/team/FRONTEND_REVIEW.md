# Aethos PS — Frontend Review

> **Owner**: Rupa (UI Engineer)
> **Status**: Skeleton. Updated as the Angular app surface lands (PLAN §7).

## Quality bar

- Angular 19 standalone components, signals, control flow.
- Tailwind v3 + Angular Material 19 (dark slate theme; not vanilla MDC).
- NgRx Signals for state.
- HTTP via `HttpClient` with interceptors (auth, tenant, error).
- SSE for chat streaming.
- Supabase JS for auth (PKCE), storage uploads, realtime channels.
- Dark theme compliance verified on every PR.
- Loading + error + empty states explicit.
- Money rendering: `| currency` pipe (never `parseFloat`).
- Keyboard navigable; ARIA labels.
- `ng lint` green.
- Playwright e2e test exists for the scenario and is not marked `test.fixme()`.

## Architecture (current snapshot)

To be filled when first feature ships:
- Routing map (lazy-loaded feature modules).
- State store organisation (NgRx Signals).
- Shared component library.
- Design tokens vs. inline styles.

## Review triggers

- After any new component / route / store.
- After any change to `frontend/src/app/core/`.
- After any agent integration (chat tool-call rendering, HITL card).
- Weekly: full frontend health review on demand.

## Changelog

### [2026-05-19] — Skeleton created.
