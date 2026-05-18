# Karya — Backend Engineering Skills

## Skill: Package Verification Protocol (MANDATORY before any third-party integration)

**Never assume a package's module structure, submodule paths, class names, or method signatures from memory. Major versions introduce breaking changes — code written against v2 will silently fail on v4.**

### Step 1 — Confirm the package is installed and check its version

```bash
# Always use the project's virtualenv, not the system Python
.venv/bin/python -c "import <package>; print(<package>.__version__)"
# or
uv pip show <package>
```

If the package is NOT installed: add it to `pyproject.toml` first, then install it:
```bash
# Add to pyproject.toml dependencies, then:
uv pip install <package>
```

### Step 2 — Discover the actual module structure

```bash
# List top-level submodules
.venv/bin/python -c "
import pkgutil, <package> as pkg
print([m.name for m in pkgutil.iter_modules(pkg.__path__)])
"

# List public API of a specific class or module
.venv/bin/python -c "import <package>; print([x for x in dir(<package>) if not x.startswith('_')])"
```

### Step 3 — Verify the exact class/method signature before writing code

```bash
.venv/bin/python -c "
import inspect
from <package> import <ClassName>
print(inspect.signature(<ClassName>.__init__))
# or for a method:
print(inspect.signature(<ClassName>.<method>))
"
```

### Step 4 — Do a minimal import smoke test before writing the full integration

```bash
.venv/bin/python -c "
from <package>.<submodule> import <ClassName>
print('import OK')
"
```

If this fails, the submodule path doesn't exist — do NOT use it. Go back to Step 2.

### Real example of what this prevents

```bash
# BAD — written from memory, will fail at runtime:
from langfuse.opentelemetry import LangfuseSpanExporter  # module doesn't exist in v4

# Correct workflow:
# Step 1: .venv/bin/python -c "import langfuse; print(langfuse.__version__)"
# → 4.5.1
# Step 2: list submodules → ['openai', 'langchain', 'api', ...]  (no 'opentelemetry')
# Step 4: from langfuse.opentelemetry import ... → ImportError confirmed
# Fix: use standard OTLPSpanExporter with Langfuse's OTLP endpoint instead
```

### When this protocol is required

- Any new `import` from a third-party package you haven't used in this session
- Any package that has had a major version update (v1→v2, v3→v4, etc.)
- Any integration with an observability, AI, or cloud SDK (these change frequently)
- When a package was added to `pyproject.toml` but may not yet be installed in `.venv`

## Skill: FastAPI Service Layer Pattern

Always follow: **Router → Service → Repository**. Never put business logic in routers.

### New Feature Template
```python
# 1. app/models/my_feature.py — Pydantic schemas
from pydantic import BaseModel, Field
from decimal import Decimal

class MyFeatureCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=0, description="Must be positive")

class MyFeatureResponse(BaseModel):
    id: str
    name: str
    amount: str  # Always serialize Decimal as string for JSON

# 2. app/repositories/my_feature_repo.py — Data access
class MyFeatureRepository:
    def __init__(self, db, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def create(self, data: dict) -> dict:
        data["tenant_id"] = self.tenant_id
        return self.db.table("my_features").insert(data).execute().data[0]

    async def get_by_id(self, id: str) -> dict | None:
        result = self.db.table("my_features") \
            .select("*").eq("id", id).eq("tenant_id", self.tenant_id) \
            .execute()
        return result.data[0] if result.data else None

# 3. app/services/my_feature_service.py — Business logic
from app.domain.money import to_money
from app.domain.rules import check_positive_amount

class MyFeatureService:
    def __init__(self, repo: MyFeatureRepository, journal_svc: JournalService):
        self.repo = repo
        self.journal_svc = journal_svc

    async def create(self, data: MyFeatureCreate) -> dict:
        amount = to_money(data.amount)
        check_positive_amount(amount)  # VR-01
        result = await self.repo.create({"name": data.name, "amount": str(amount)})
        return result

# 4. app/api/v1/my_feature_router.py — Thin router
from fastapi import APIRouter, Depends
from app.core.auth import require_permission, get_tenant_from_header

router = APIRouter(prefix="/my-features", tags=["my-features"])

@router.post("/", response_model=MyFeatureResponse)
async def create(
    payload: MyFeatureCreate,
    tenant_id: str = Depends(get_tenant_from_header),
    _auth = Depends(require_permission("my_features:create")),
):
    service = MyFeatureService(...)
    return await service.create(payload)
```

## Skill: PydanticAI Agent Integration

```python
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from app.agents.base import AgentDeps, run_agent_safe, mask_pii

class MyAgentOutput(BaseModel):
    classification: str
    confidence: float
    reasoning: str

my_agent = Agent(
    'anthropic:claude-sonnet-4-6',
    deps_type=AgentDeps,
    output_type=MyAgentOutput,
    instructions="You are a financial classification agent...",
    retries=2,
)

@my_agent.tool
async def fetch_data(ctx: RunContext[AgentDeps], query: str) -> str:
    result = ctx.deps.db.table("table_name") \
        .select("*").eq("tenant_id", ctx.deps.tenant_id).execute()
    return mask_pii(str(result.data))  # Never send raw PII

# In service layer:
async def classify(self, data: dict) -> MyAgentOutput:
    result = await run_agent_safe(
        my_agent,
        deps=AgentDeps(db=self.db, tenant_id=self.tenant_id),
        prompt=f"Classify this transaction: {mask_pii(str(data))}",
        fallback=MyAgentOutput(classification="uncategorized", confidence=0.0, reasoning="Agent unavailable"),
    )
    return result
```

## Skill: Database Migration Checklist

Before any schema change:
- [ ] Add `tenant_id` column with NOT NULL
- [ ] Add RLS policy: `CREATE POLICY ... USING (tenant_id = current_setting('app.current_tenant_id'))`
- [ ] Use `NUMERIC(15,2)` for monetary columns
- [ ] Add proper indexes for query patterns
- [ ] Test with multi-tenant data to verify RLS
- [ ] Add `created_at` and `updated_at` timestamps
- [ ] Use `deleted_at` for soft deletes (never hard delete financial records)

## Skill: Secure Coding Checklist

Run through this before every PR. Flag anything not satisfied and resolve before opening for review.

### Input Validation
- [ ] All Pydantic models use field constraints: `min_length`, `max_length`, `gt`, `le`, `pattern`
- [ ] `str` fields that map to DB columns have `max_length` — prevents oversized payload attacks
- [ ] Numeric fields use `Decimal`, never `float` — prevents precision manipulation
- [ ] File uploads validate MIME type server-side — never trust `Content-Type` header alone
- [ ] No user input is interpolated directly into SQL strings — use Supabase query builder always

### Auth & Authorization
- [ ] Every endpoint has `Depends(require_permission("resource:action"))` — no unguarded routes
- [ ] Use `get_service_db()` ONLY when intentional (RBAC lookups, super admin ops) — document why
- [ ] All queries include `.eq("tenant_id", tenant_id)` even when RLS is active — defense in depth
- [ ] Sensitive endpoints (payments, GL posting) have rate limiting applied

### Error Handling — Never Leak Internals
```python
# BAD — exposes stack trace and internal details to API consumers
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

# GOOD — log internally with full context, return generic message externally
except Exception as e:
    logger.error(f"Failed to create payment: {str(e)}", exc_info=True)
    raise HTTPException(status_code=500, detail="An internal error occurred")
```

### Secrets & Sensitive Data
- [ ] No secrets, API keys, or credentials in code or log statements
- [ ] PII masked before passing to any agent: `mask_pii(str(data))` in `app/agents/base.py`
- [ ] Agent tool results that contain PII are masked before logging
- [ ] `SUPABASE_SERVICE_ROLE_KEY` never referenced in business logic — only in `core/db.py`

### HTTP Security Headers (add to `app/main.py` middleware)
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

# Add security headers via middleware or response hook
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

### Agent Security
- [ ] All agent tool inputs validated before use — agents don't bypass Pydantic validation
- [ ] `run_agent_safe()` used for all agent calls — never call `.run()` directly (no fallback)
- [ ] Agent fallback returns a safe default, not an empty dict that could break downstream logic
- [ ] No agent tool constructs DB queries from raw LLM output
