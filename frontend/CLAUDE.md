# Aethos PS — Frontend instructions (Rupa / Chitra / Aksha)

Read the root [`CLAUDE.md`](../CLAUDE.md) first. This file is the frontend-specific overlay referenced by `docs/team/SDLC_PROTOCOL.md`.

## Stack (as built)
- Angular 20.3 standalone components, signals, control flow (`@if/@for/@defer`), typed reactive forms. **No NgRx** — state is component/service signals.
- Tailwind v3 + Angular Material (dark slate theme via `src/assets/brand/themes`). Node 20.19 (`.nvmrc`).
- Two apps in one workspace: `aethos-ps` (`src/`, port 4201) and `timesheet` (`projects/timesheet`, employee portal, prod port 4202).
- Supabase JS for auth; all API calls are relative `/api/v1/...` through `core/interceptors/auth.interceptor.ts` (adds `Authorization` + `X-Tenant-ID`). The Nous SSE path uses `fetch` with hand-built headers (`features/copilot/copilot.component.ts`).

## Layout
```
src/app/core/        auth.service, guards (authGuard/authChildGuard), interceptors, domain services (reports, hitl, engagement, expenses, time-entries, billing-runs = Pay Bills)
src/app/shared/      shell (top nav, no sidebar), money pipe (display only), confidence chip, decision timeline, empty/skeleton states
src/app/features/    one folder per route (see app.routes.ts); settings/ holds ~20 panels rendered on one page
src/app/features/guides/  public guide library generated from docs/*.md by scripts/generate-guides.mjs (run `npm run guides:generate`)
e2e/                 Playwright specs; global.setup.ts logs in with e2e/.auth/o2c-tenant.meta.json (specs self-skip without it)
```

## Rules
- Money arrives as strings; display with `| money`; **never** `parseFloat`/`Number()` for arithmetic (#508) — compute in integer minor units or let the API compute.
- Every list/detail renders loading, error (with retry, `role="alert"`) and empty states.
- Keyboard + ARIA: focus-visible rings, `aria-label` on icon buttons, `role="dialog" aria-modal` on drawers; keyboard shortcuts must ignore text inputs (#494).
- Responsive: no horizontal page scroll at 390 px (#510).
- Never approve on behalf of an "Edit" action (#507); route to the Inbox drawer.
- Nous UI must not expose tool names, traces, or raw payloads (#480).

## Commands
```bash
npm ci
npm start                      # ng serve --port 4201 (regenerates guides first)
npm run typecheck              # both apps + specs (CI)
npm run test:ci                # Karma, aethos-ps app only (timesheet has no test target yet — #511)
npm run build:all              # production builds for both apps
npx playwright test --project=chromium          # needs API :8011 + web :4201 + e2e/.auth fixture
```
`npm run lint` fails: no lint target exists (#495).

## Closure evidence
UI-touching issues close only with a passing Playwright spec under `e2e/` or a Founder-confirmed browser walkthrough with screenshot (`docs/team/SDLC_PROTOCOL.md`).
