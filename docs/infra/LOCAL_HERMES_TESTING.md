# Local Hermes Runtime — Build, Run, and Verify

How to run the Hermes-powered Nous runtime locally (matching prod) so the full
`API → Hermes → MCP tool broker → Aethos` path can be tested before deploying.

This uses a hybrid: **Hermes runs in Docker, pointed at the host-run API**
(`host.docker.internal`), so you don't have to containerise the whole stack.

## Prerequisites

- Docker running.
- The host API running on `:8011` (see the backend run command).
- A seeded tenant (see `docs/DEMO_GUIDE_v2.md` Pre-Demo Setup).
- `.env` populated with the shared Hermes tokens (already present):
  `HERMES_API_SERVER_KEY` (== `ATLAS_HERMES_API_SERVER_KEY`),
  `AETHOS_HERMES_TOOL_TOKEN`, `ATLAS_CONTEXT_SIGNING_SECRET`, `OPENROUTER_API_KEY`.

## 1. Build the Hermes image

```bash
docker build -t aethos-ps-hermes:local integrations/hermes/
```

The image is `nousresearch/hermes-agent:latest` plus the Aethos profile
(`SOUL.md`, `config.yaml`, skills, and `aethos_mcp_server.py`). The profile's
`config.yaml` registers the `aethos` MCP server, which Hermes imports into its
MCP registry on start.

## 2. Run Hermes, pointed at the host API

```bash
set -a && source .env && set +a
docker run -d --name aethos-hermes -p 8642:8642 \
  --add-host=host.docker.internal:host-gateway \
  -e API_SERVER_ENABLED=true -e API_SERVER_HOST=0.0.0.0 -e API_SERVER_PORT=8642 \
  -e API_SERVER_KEY="$HERMES_API_SERVER_KEY" \
  -e API_SERVER_MODEL_NAME="Aethos Nous" -e HERMES_DASHBOARD=0 \
  -e AETHOS_HERMES_REFRESH_PROFILE=true \
  -e AETHOS_INTERNAL_API_URL="http://host.docker.internal:8011" \
  -e AETHOS_HERMES_TOOL_TOKEN="$AETHOS_HERMES_TOOL_TOKEN" \
  -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
  aethos-ps-hermes:local
```

Wait for health: `curl http://localhost:8642/health` → `{"status":"ok",...}`.

Verify the tool broker connection and tool discovery:

```bash
docker exec aethos-hermes hermes mcp test aethos
```

You should see the `aethos_*` tools listed (engagements, finance, r2r, etc.).

## 3. Point the host API at the local Hermes

Restart the API with the Hermes runtime and the local Hermes URL:

```bash
cd backend && set -a && source ../.env && set +a
export ATLAS_AI_RUNTIME=hermes_agent
export ATLAS_HERMES_API_BASE_URL=http://localhost:8642
export ATLAS_HERMES_FALLBACK_TO_BASIC=true
uv run uvicorn app.main:app --host 0.0.0.0 --port 8011
```

Optionally force the pure Hermes path for a tenant (bypass the semantic router):

```sql
insert into tenant_ai_settings (tenant_id, atlas_runtime, semantic_router_enabled)
values ('<tenant-uuid>', 'hermes_agent', false)
on conflict (tenant_id) do update
set atlas_runtime = excluded.atlas_runtime,
    semantic_router_enabled = excluded.semantic_router_enabled;
```

## 4. Verify a live Hermes turn

Run the opt-in agent eval against the tenant — it now exercises Hermes:

```bash
cd backend
AETHOS_EVAL_LIVE=1 AETHOS_EVAL_API_URL=http://localhost:8011 \
AETHOS_EVAL_TOKEN=<jwt> AETHOS_EVAL_TENANT_ID=<tenant-uuid> \
uv run pytest tests/eval/test_agent_eval_live.py -q -s
```

Confirm the answer is real (matches Reports) and that the API log shows **no**
`atlas_provider_failure` for the turn (a failure means it fell back to Basic).

## Gotchas discovered

- **Model matters.** The free `google/gemma-4-31b-it:free` has a 16k-token quota
  that this tool-heavy agent exhausts (HTTP 429), causing constant fallback.
  `config.yaml` `model.default` is set to a reliable paid model
  (`anthropic/claude-haiku-4.5`).
- **Hermes does not env-substitute `${VAR}` in `model.default`** — set it
  literally. It does resolve MCP-server env from the container environment.
- **MCP registration** comes from `config.yaml` `mcp_servers` (imported into the
  Hermes MCP registry on start), not the empty `mcp.json`. Confirm with
  `hermes mcp test aethos`.
- The API's built-in **fallback to the Basic runtime** means users still get
  correct answers even when Hermes/its provider is down — so always check the
  logs to confirm a turn actually used Hermes, not just that it answered.
