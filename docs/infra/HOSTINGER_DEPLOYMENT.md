# Hostinger Production Deployment

This guide deploys Aethos PS to a Hostinger VPS that already runs Docker and
Traefik. On this VPS, Traefik runs in `host` network mode with the Docker
provider enabled and `exposedByDefault=false`, so public containers are routed
by labels.

## Target URLs

- Main app: `https://aethos.ishirock.tech`
- Timesheet portal: `https://timesheet.aethos.ishirock.tech`

Both DNS A records must point to the Hostinger VPS public IP.

## Runtime Shape

The API is private. Traefik only routes to the nginx web containers:

```text
Traefik
  -> frontend:80  -> /api/* -> api:8080
  -> timesheet:80 -> /api/* -> api:8080

worker -> Supabase Postgres queue, when `DATABASE_URL` is configured
```

No public route is created directly to the API container.

## Traefik Labels

The Hostinger compose file uses the same label pattern as the existing VPS
apps.

Main app:

```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.aethos.rule=Host(`aethos.ishirock.tech`)
  - traefik.http.routers.aethos.entrypoints=websecure
  - traefik.http.routers.aethos.tls.certresolver=letsencrypt
  - traefik.http.services.aethos.loadbalancer.server.port=80
```

Timesheet portal:

```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.aethos-timesheet.rule=Host(`timesheet.aethos.ishirock.tech`)
  - traefik.http.routers.aethos-timesheet.entrypoints=websecure
  - traefik.http.routers.aethos-timesheet.tls.certresolver=letsencrypt
  - traefik.http.services.aethos-timesheet.loadbalancer.server.port=80
```

## Files

- `docker-compose.hostinger.yml`
- `scripts/deploy/hostinger-deploy.sh`
- `.github/workflows/deploy-hostinger.yml`
- `docs/infra/LANGFUSE_OBSERVABILITY.md`
- `docs/infra/PRODUCTION_DATA_RESET.md`

## Required Local `.env` Values

These values are for deployment tooling:

```bash
HOSTINGER_API_KEY=...
HOSTINGER_VM_ID=1695814
HOSTINGER_APP_DOMAIN=aethos.ishirock.tech
HOSTINGER_TIMESHEET_DOMAIN=timesheet.aethos.ishirock.tech
TRAEFIK_ENTRYPOINT=websecure
TRAEFIK_CERT_RESOLVER=letsencrypt
```

For manual SSH deploys, also add:

```bash
HOSTINGER_SSH_HOST=<vps-ip-or-hostname>
HOSTINGER_SSH_USER=root
HOSTINGER_SSH_PORT=22
HOSTINGER_APP_DIR=/opt/aethos-ps
HOSTINGER_DEPLOY_SOURCE=git
HOSTINGER_BRANCH=main
```

Use `HOSTINGER_DEPLOY_SOURCE=local` for a first rollout before the Hostinger
deployment files have been committed and pushed. In local mode, the deploy
script syncs only:

- `backend/`
- `frontend/`
- `integrations/`
- `docker-compose.hostinger.yml`

After the deployment files are on `main`, switch back to
`HOSTINGER_DEPLOY_SOURCE=git` so production deploys come from reviewed source.

## Background Worker

The worker is behind the Compose profile `worker`.

Manual SSH deploys enable this profile automatically when `DATABASE_URL` is
present in the generated runtime env. If `DATABASE_URL` is empty, the script
deploys only `api`, `frontend`, and `timesheet`.

GitHub Action deploys should set this repository variable when the worker is
ready:

```text
COMPOSE_PROFILES=worker
```

Use the Supabase session pooler connection string on port `5432`, not the
transaction pooler on `6543`, because Procrastinate uses LISTEN/NOTIFY.

Do not use the direct Supabase host form:

```text
postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

For this project that host resolves to IPv6 only. The Hostinger VPS can resolve
it, but Docker bridge containers cannot reach it without enabling IPv6 for
Docker. Use the Supabase pooler form instead:

```text
postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

## Optional Hermes-Powered Atlas Runtime

Atlas now supports configurable AI runtimes behind the same `/api/v1/chat/*`
routes:

```text
ATLAS_AI_RUNTIME=aethos_basic   # default, current built-in Atlas AI
ATLAS_AI_RUNTIME=hermes_agent   # advanced Hermes-powered Atlas runtime
```

The Hermes container is optional and behind the Compose profile `hermes`. The
current Hostinger production deployment runs Hermes as the primary Atlas runtime
with the built-in Aethos runtime enabled as a fallback:

```text
COMPOSE_PROFILES=worker,hermes
ATLAS_AI_RUNTIME=hermes_agent
ATLAS_HERMES_FALLBACK_TO_BASIC=true
```

To start Hermes on Hostinger, also set:

```text
COMPOSE_PROFILES=worker,hermes
HERMES_API_SERVER_KEY=<long-random-token>
ATLAS_HERMES_API_SERVER_KEY=<same-token>
ATLAS_HERMES_API_BASE_URL=http://hermes:8642
ATLAS_HERMES_FALLBACK_TO_BASIC=true
HERMES_OPENROUTER_API_KEY=<optional-dedicated-hermes-provider-key>
ATLAS_BASIC_OPENROUTER_API_KEY=<optional-dedicated-basic-fallback-provider-key>
ATLAS_BASIC_OPENROUTER_BASE_URL=<optional-basic-fallback-openai-compatible-url>
ATLAS_HIDE_TOOL_EVENTS=true
AETHOS_HERMES_TOOL_TOKEN=<different-long-random-token>
ATLAS_CONTEXT_SIGNING_SECRET=<long-random-token-or-empty-to-use-SUPABASE_JWT_SECRET>
AETHOS_HERMES_REFRESH_PROFILE=true
AGENT_MODELS=google/gemma-4-31b-it:free,openrouter/free,anthropic/claude-haiku-4.5
```

Hermes is private on the internal Docker network. Do not add Traefik labels for
the in-app Atlas migration. A public route should only be added later for
external-channel webhooks, and the Hermes API server/dashboard should remain
private.

The Hermes-powered Atlas runtime uses a private Aethos Tool Broker:

- Aethos API exposes `/api/v1/atlas-tools/execute` on the internal network.
- Hermes accesses it only through the bundled `aethos` MCP server in the
  `aethos-ps-hermes` image.
- Aethos signs a short-lived `context_ref` per Atlas turn. Hermes passes that
  opaque value to tools; tenant and user scope are derived by Aethos, not by
  model-supplied arguments.
- The initial MCP allowlist includes read-only finance tools plus guarded
  workflow tools: engagement list, AR aging, AP aging, WIP, finance ops
  snapshot, finance action plan, invoice draft, collections reminder drafts,
  bill-pay proposal, month-end/year-end close preparation, and statement
  package generation. Guarded workflows use Aethos policy and Inbox; they do
  not directly approve invoices, payments, journals, statements, or emails.
- `AETHOS_HERMES_REFRESH_PROFILE=true` keeps the managed Atlas profile, skills,
  and MCP config current across image upgrades without deleting Hermes memory or
  session data.
- Default OpenRouter routing for Aethos-owned inference is Gemma 4 31B free,
  then OpenRouter's free model router, then Claude Haiku 4.5:
  `google/gemma-4-31b-it:free,openrouter/free,anthropic/claude-haiku-4.5`.
  Tenant admins can view and override runtime/model routing from Settings ->
  Agent Autonomy -> AI Inference Settings. These tenant settings apply to
  Aethos Basic, the built-in fallback path, and tenant-scoped document/reporting
  agents. Hermes still uses the mounted Atlas profile for its primary model
  until Hermes exposes dynamic per-tenant model selection.
- Hermes provider/control-plane failures are classified as infrastructure
  failures by the Aethos API. Atlas should show a short user-safe unavailable
  message or fall back to the built-in runtime; it must not show provider URLs,
  billing/key-limit text, traces, or raw tool output to end users.
- For enterprise resilience, do not point Hermes and the built-in fallback at
  the same exhausted provider key. Set `HERMES_OPENROUTER_API_KEY` for Hermes
  and `ATLAS_BASIC_OPENROUTER_API_KEY` for the built-in fallback when separate
  OpenRouter workspaces/keys are available. If the fallback key is empty, the
  built-in runtime uses `OPENROUTER_API_KEY`.

## Manual Deploy

From the repo root:

```bash
scripts/deploy/hostinger-deploy.sh
```

The script:

1. Reads the local `.env`.
2. Generates a temporary production runtime env.
3. Excludes `HOSTINGER_API_KEY` and `HOSTINGER_VM_ID` from container runtime.
4. Forces:
   - `DEBUG=false`
   - `ENVIRONMENT=production`
   - `FRONTEND_BASE_URL=https://aethos.ishirock.tech`
   - `CORS_ORIGINS=https://aethos.ishirock.tech,https://timesheet.aethos.ishirock.tech`
5. SSHes to the VPS.
6. Clones/updates the repo in `/opt/aethos-ps`, or syncs local app sources when
   `HOSTINGER_DEPLOY_SOURCE=local`.
7. Runs:

```bash
docker compose \
  --project-name aethos-ps \
  --env-file .env.hostinger \
  -f docker-compose.hostinger.yml \
  up -d --build --remove-orphans
```

## GitHub Action Deploy

The workflow is manual-only for now:

```text
Actions -> Deploy Hostinger Production -> Run workflow
```

Required GitHub Actions secret:

- `HOSTINGER_API_KEY`

Required GitHub Actions variable:

- `HOSTINGER_VM_ID=1695814`

Recommended GitHub Actions secret:

- `AETHOS_PRODUCTION_ENV`

`AETHOS_PRODUCTION_ENV` should contain the production app env lines, excluding
deployment-only values such as `HOSTINGER_API_KEY`.

Optional GitHub Actions variables:

- `TRAEFIK_ENTRYPOINT`
- `TRAEFIK_CERT_RESOLVER`
- `COMPOSE_PROFILES=worker`
- `COMPOSE_PROFILES=worker,hermes` when testing Hermes-powered Atlas

## Production Integrations To Update

Stripe webhook:

```text
https://aethos.ishirock.tech/api/v1/webhooks/stripe
```

Stripe Connect redirect:

```text
https://aethos.ishirock.tech/settings/billing/connect/return
```

Supabase auth/site URLs should allow:

```text
https://aethos.ishirock.tech
https://timesheet.aethos.ishirock.tech
```

## Smoke Checks

After deploy:

```bash
curl -fsS https://aethos.ishirock.tech/health
curl -fsS https://aethos.ishirock.tech/api/v1/ping
curl -fsS https://timesheet.aethos.ishirock.tech/health.txt
```

Then verify in browser:

- Sign in.
- Open Copilot.
- Upload an invoice.
- Ask AI to create a vendor bill from the upload.
- Open bill approval in Inbox.
- Open Timesheet portal and load current week entries.

If this is a clean production reset, follow
`docs/infra/PRODUCTION_DATA_RESET.md` after the deploy smoke checks pass.
