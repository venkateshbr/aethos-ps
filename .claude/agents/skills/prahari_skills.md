# Prahari — Security Review Skills

## Skill: OWASP Top 10 Audit Checklist (FastAPI + Supabase + Angular)

### A01 — Broken Access Control
- [ ] Every router endpoint has `Depends(require_permission("resource:action"))` — no unprotected routes
- [ ] `get_current_user` is called before any data access — no endpoints that bypass auth
- [ ] IDOR check: all queries include `.eq("tenant_id", tenant_id)` — user cannot access another tenant's records by guessing IDs
- [ ] Super admin endpoints use `Depends(get_current_super_admin)` — not just `get_current_user`
- [ ] RLS policies exist on ALL tables with tenant data — verify with: `SELECT tablename, policyname FROM pg_policies WHERE schemaname='public'`
- [ ] `get_service_db()` (service role key) is used ONLY where intentional and justified — audit every usage
- [ ] Horizontal privilege escalation: a `viewer` cannot POST/PUT/DELETE — test with role downgrade
- [ ] Path traversal: no file paths constructed from user input without sanitization

### A02 — Cryptographic Failures
- [ ] `JWT_SECRET` is never the default value in production — check env var enforcement in `app/core/auth.py`
- [ ] Passwords hashed with bcrypt (cost ≥ 12) — never MD5, SHA-1, or plain text
- [ ] No sensitive data (PII, bank details, tax IDs) stored unencrypted
- [ ] HTTPS enforced — HTTP requests redirected (check nginx/proxy config)
- [ ] JWT algorithm is `HS256` minimum — `alg: none` not accepted
- [ ] Database backups encrypted at rest

### A03 — Injection
- [ ] All Supabase queries use parameterized builder pattern — `.eq()`, `.filter()`, `.select()` — never f-string SQL
- [ ] No raw SQL via `supabase.rpc()` with unvalidated user input
- [ ] Pydantic models validate all incoming data — `str` fields have `max_length`, numeric fields have `gt=0`
- [ ] File uploads: validate MIME type and extension server-side — never trust `Content-Type` header alone
- [ ] Agent prompts: user input is sanitized/masked before injecting into LLM prompt — check `mask_pii()`

### A04 — Insecure Design
- [ ] HITL checkpoint exists for any agent action with financial consequence (payment creation, GL posting)
- [ ] Rate limiting on all authentication endpoints — check `RateLimiter` in `app/api/auth.py`
- [ ] Financial transactions are idempotent — duplicate POST does not create duplicate payment
- [ ] Period lock enforced before any financial write — not bypassable via API parameter
- [ ] Agent autonomy level L3 only for `accounting_guardian` — all others default L1 or L2

### A05 — Security Misconfiguration
- [ ] CORS: `allow_origins` is NOT `["*"]` in production — check `app/main.py`
- [ ] Debug mode OFF in production — `DEBUG=False`, no `/docs` or `/redoc` exposed publicly
- [ ] Stack traces not returned in 500 responses — `detail=str(e)` in exception handlers leaks internals
- [ ] Security headers present: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`
- [ ] `SUPABASE_SERVICE_ROLE_KEY` never logged — check log statements in `app/core/db.py`
- [ ] No `.env` files committed — check `.gitignore`

### A06 — Vulnerable Components
- [ ] `pip-audit` runs in CI with zero HIGH/CRITICAL findings allowed
- [ ] `npm audit --audit-level=high` runs in CI
- [ ] Dependencies pinned to exact versions in `pyproject.toml` / `package-lock.json`
- [ ] Base Docker image is not `latest` — pinned to specific digest

### A07 — Authentication Failures
- [ ] Brute force protection: rate limiter on `/auth/login` — max 5/min per IP
- [ ] JWT expiry enforced — tokens expire in 24h, no "never expire" tokens
- [ ] Expired token returns 401 not 200 — test with manually expired token
- [ ] No JWT secret in client-side code or Angular environment files
- [ ] Password change requires old password — cannot reset to anything without verification
- [ ] Session invalidation: logout actually invalidates token server-side (or is stateless with short expiry)

### A08 — Software Integrity Failures
- [ ] GitHub Actions use pinned SHA for third-party actions — not `@main` or `@v1`
- [ ] No `eval()` or `exec()` with user-controlled input in Python
- [ ] No `innerHTML` or `bypassSecurityTrust*` in Angular without explicit justification

### A09 — Logging & Monitoring Failures
- [ ] Auth failures logged with IP, user, and timestamp
- [ ] Failed permission checks logged — `require_permission` failures auditable
- [ ] Agent executions logged to `agent_audit_log` — with tenant, user, action, result
- [ ] PII masked in logs — no email, tax ID, bank account numbers in plain log text
- [ ] Alerts configured for: multiple auth failures, unusual tenant data volume, agent errors

### A10 — SSRF
- [ ] Any URL provided by user is validated against allowlist before HTTP call
- [ ] Webhook URL registration validates protocol (https only) and blocks private IP ranges
- [ ] LLM agent tools that fetch URLs validate target before fetching

---

## Skill: Tenant Isolation Audit

Run these queries in Supabase SQL editor to audit RLS coverage:

```sql
-- Tables without RLS enabled
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename NOT IN (
    SELECT DISTINCT tablename FROM pg_policies WHERE schemaname = 'public'
  );

-- Tables with RLS enabled but no policies
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND rowsecurity = true
  AND tablename NOT IN (
    SELECT DISTINCT tablename FROM pg_policies WHERE schemaname = 'public'
  );

-- All RLS policies (audit for tenant_id clause)
SELECT tablename, policyname, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename;

-- Verify get_current_tenant_id function exists
SELECT proname, prosrc FROM pg_proc WHERE proname = 'get_current_tenant_id';
```

Cross-tenant attack simulation (run as anon key, not service role):
```python
# Attempt to read tenant B's data while authenticated as tenant A
# Should return empty — if it returns data, RLS is broken
response = client.table("invoices").select("*").eq("tenant_id", "tenant_b_uuid").execute()
assert len(response.data) == 0, "CRITICAL: Cross-tenant data leak!"
```

---

## Skill: Auth & JWT Security Review

### JWT Claims to Verify
```python
# Decode and inspect — use for manual review only
import jwt
payload = jwt.decode(token, options={"verify_signature": False})
# Must have: exp (expiry), iat (issued at), sub (user_id), tenant_id
# Must NOT have: password_hash, service_role_key, raw PII

assert "exp" in payload, "Missing expiry — tokens never expire!"
assert "tenant_id" in payload, "Missing tenant_id — cannot enforce isolation"
assert payload["exp"] - payload["iat"] <= 86400, "Token valid > 24h — reduce expiry"
```

### Service Role Key Audit
```bash
# Find every usage of get_service_db() — each must be justified
grep -rn "get_service_db\|service_role" backend/app/ --include="*.py"
# Legitimate: auth.py (RBAC lookup), admin.py (super admin ops)
# Suspicious: any business API that could use tenant-scoped get_db() instead
```

---

## Skill: Secure Code Templates

### Input Validation — FastAPI
```python
from pydantic import BaseModel, Field, validator
from decimal import Decimal

class SecureTransactionCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, le=Decimal("9999999.99"))
    description: str = Field(..., min_length=1, max_length=500)
    reference: str = Field(..., pattern=r"^[A-Za-z0-9\-_]+$")  # Allowlist chars

    @validator("description")
    def no_script_tags(cls, v):
        if "<script" in v.lower() or "javascript:" in v.lower():
            raise ValueError("Invalid characters in description")
        return v
```

### Secure Response — Never Leak Internals
```python
# BAD — leaks stack trace and internal details
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

# GOOD — log internally, return generic message
except Exception as e:
    logger.error(f"Transaction creation failed: {str(e)}", exc_info=True)
    raise HTTPException(status_code=500, detail="An internal error occurred")
```

### PII Masking Before LLM Calls
```python
from app.agents.base import mask_pii

# Always mask before sending to external LLM
safe_input = mask_pii(raw_transaction_description)
result = await run_agent_safe(classifier_agent, prompt=safe_input, ...)
```

### Rate Limiting Pattern
```python
from app.api.auth import RateLimiter

# Apply to any sensitive mutation endpoint
sensitive_limiter = RateLimiter(max_requests=10, window_seconds=60)

@router.post("/payments/")
async def create_payment(request: Request, ...):
    client_ip = get_client_ip(request)
    if sensitive_limiter.is_rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests")
    ...
```

---

## Skill: CI/CD Security Pipeline

### GitHub Actions Security Job (add to `.github/workflows/ci.yml`)
```yaml
security-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Full history for secret scanning

    # Python SAST — static analysis for common security issues
    - name: Install Bandit
      run: pip install bandit[toml]
    - name: Run Bandit SAST
      run: bandit -r backend/app/ -ll -ii --exit-zero  # -ll = medium+, -ii = medium+ confidence
      # Change --exit-zero to fail on findings when baseline is clean

    # Python dependency audit
    - name: Run pip-audit
      run: |
        pip install pip-audit
        pip-audit --requirement backend/requirements.txt --fail-on-vuln --severity high

    # Secret detection — catches leaked keys in code/history
    - name: Run Gitleaks
      uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

    # Semgrep SAST — custom rules for FastAPI/Supabase patterns
    - name: Run Semgrep
      uses: semgrep/semgrep-action@v1
      with:
        config: >-
          p/python
          p/fastapi
          p/jwt
          p/sql-injection

    # npm audit for frontend
    - name: Frontend dependency audit
      run: npm audit --audit-level=high
      working-directory: frontend
```

### Semgrep Custom Rule — Detect Unprotected Endpoints
```yaml
# .semgrep/aethos-rules.yml
rules:
  - id: unprotected-fastapi-endpoint
    patterns:
      - pattern: |
          @$ROUTER.$METHOD(...)
          def $FUNC(...):
              ...
      - pattern-not: |
          @$ROUTER.$METHOD(...)
          def $FUNC(..., _auth = Depends(...), ...):
              ...
    message: "FastAPI endpoint $FUNC may lack auth dependency"
    severity: WARNING
    languages: [python]

  - id: service-role-without-justification
    pattern: get_service_db()
    message: "Using service role key bypasses RLS — ensure this is intentional"
    severity: INFO
    languages: [python]
```

---

## Skill: Security Review Report Template

```markdown
## Security Review: [PR/Feature/Component Name]
**Date**: YYYY-MM-DD
**Reviewer**: Prahari
**Scope**: [Files/endpoints reviewed]
**Risk Level**: 🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low

### Findings

#### FINDING-001: [Title]
- **Severity**: Critical / High / Medium / Low
- **OWASP**: A0X — [Category]
- **CWE**: CWE-XXX
- **Location**: `file/path.py:line_number`
- **Description**: [What the vulnerability is]
- **Impact**: [What an attacker can do — data at risk]
- **Fix**:
  ```python
  # Before (vulnerable)
  ...
  # After (fixed)
  ...
  ```
- **GitHub Issue**: #XXX

### Security Posture Summary
| Category | Status | Notes |
|---|---|---|
| Authentication | ✅ Pass / ⚠️ Warn / ❌ Fail | |
| Authorization | | |
| Input Validation | | |
| Tenant Isolation | | |
| Cryptography | | |
| Logging | | |
| Dependencies | | |

### Recommendations
1. [Highest priority item]
2. [Next priority]

### Sign-off
- [ ] All Critical findings resolved
- [ ] High findings resolved or risk-accepted by Vishwa
- [ ] Regression tests added by Aksha for each finding
```
