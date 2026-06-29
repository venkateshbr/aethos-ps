# Langfuse Observability

Aethos uses Langfuse as the LLM observability layer for agent calls that go
through the shared OpenAI/OpenRouter client factory.

## Required Environment

Configure these values in the API and worker runtime:

```bash
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_TRACING_ENABLED=true
LANGFUSE_SAMPLE_RATE=1.0
```

`LANGFUSE_BASE_URL` should match the Langfuse region for the project.

## Instrumented Agent Calls

The shared factories in `backend/app/agents/base.py` wrap Langfuse's OpenAI
drop-in client when keys are present:

- `make_async_llm_client(...)`
- `make_sync_llm_client(...)`

The wrapper keeps OpenRouter as the model gateway and injects Langfuse metadata
on every chat completion:

- `environment`
- `tenant_id`
- request `trace_id` when available
- `agent_name`
- `user_id` / `langfuse_user_id`
- `langfuse_session_id`
- `langfuse_tags`
- workflow-specific metadata such as `document_id`, `document_mime_type`,
  anomaly type, and extraction stage

Current tagged agent surfaces:

- Copilot agent
- vendor invoice extraction, vendor matching, and GL suggestion calls
- expense extraction
- engagement letter extraction
- reporting agent narrative generation
- intelligence alert narrative generation

The API flushes Langfuse during FastAPI shutdown. The worker also gets an
`atexit` flush through the shared agent module.

## Internal Ledger Boundary

Langfuse captures model-level traces, latency, usage, prompts, completions, and
errors. Aethos still keeps internal control evidence in:

- `agent_runs`
- `agent_tool_invocations`
- `agent_suggestions`
- `hitl_tasks`
- financial/event audit tables

Use Langfuse for LLM observability and token economics. Use the Aethos ledger
for tenant-scoped business approvals, replay evidence, and financial controls.

## Verification

Local tests:

```bash
cd backend
uv run pytest tests/unit/test_langfuse_observability.py -q
```

Production smoke after deploy:

```bash
docker exec aethos-ps-api-1 python -c "import langfuse; print('langfuse_sdk=ok')"
docker exec aethos-ps-worker-1 python -c "import langfuse; print('langfuse_sdk=ok')"
```

Then trigger any Copilot or document extraction prompt. A trace should appear
in Langfuse with tags such as `env:production` and `agent:copilot_agent`.
