# Sthira — SRE & DevOps Skills

## Skill: Package Installation Protocol

**When Karya or any agent adds a package to `pyproject.toml`, it is NOT automatically installed in the running virtualenv.** Always complete the install step.

```bash
# After any pyproject.toml dependency addition:
cd erpcore/backend && uv pip install -e .
# or install the specific package directly:
uv pip install <package>

# Confirm install succeeded before any other work:
.venv/bin/python -c "import <package>; print(<package>.__version__)"
```

**Also ensure packages added to `pyproject.toml` are reflected in your Docker image / CI build.** A package present locally but absent from the container will cause silent failures in production.

## Skill: CI/CD Pipeline Template (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI Pipeline
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
        working-directory: backend
      - run: ruff check .
        working-directory: backend
      - run: pytest --cov=app --cov-report=xml
        working-directory: backend
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
        working-directory: frontend
      - run: npm run lint
        working-directory: frontend
      - run: npm test -- --no-watch --code-coverage
        working-directory: frontend

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for secret scanning

      # SAST — Bandit for Python security issues
      - name: Run Bandit SAST
        run: |
          pip install bandit[toml]
          bandit -r backend/app/ -ll -ii --format json -o bandit-report.json || true
        working-directory: .

      # Python dependency vulnerability audit
      - name: Run pip-audit
        run: |
          pip install pip-audit
          pip-audit -r backend/requirements.txt --fail-on-vuln --severity high
        working-directory: .

      # Semgrep — pattern-based SAST (FastAPI, JWT, SQL injection)
      - name: Run Semgrep
        uses: semgrep/semgrep-action@v1
        with:
          config: "p/python p/fastapi p/jwt p/secrets"

      # Secret detection — catches leaked API keys/tokens in commits
      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      # npm audit for frontend
      - name: npm audit
        run: npm audit --audit-level=high
        working-directory: frontend
```

## Skill: Docker Multi-Stage Build

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e "."

FROM python:3.12-slim AS runtime
RUN useradd --create-home appuser
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
USER appuser
EXPOSE 8010
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
```

## Skill: Runbook Entry Template

```markdown
## Runbook: [Incident/Procedure Name]

### Severity: P[1-4]
### Estimated Resolution Time: [minutes]

### Symptoms
- [What the user/monitoring sees]

### Root Cause
- [Why this happens]

### Resolution Steps
1. [Exact command or action]
2. [Next step]
3. [Verification step]

### Rollback
1. [How to undo if resolution fails]

### Prevention
- [What to do to prevent recurrence]
```

## Skill: Observability Checklist

- [ ] Structured JSON logging (not plain text)
- [ ] Request ID propagated through all layers
- [ ] Agent execution time metrics
- [ ] API latency P50/P95/P99 tracked
- [ ] Error rate alerts configured
- [ ] Database query latency monitored
- [ ] LLM API timeout rate tracked
- [ ] Disk/memory usage alerts set
- [ ] Health check endpoint returning status of all dependencies

## Skill: Infrastructure Security Checklist

### Secrets Management
- [ ] All secrets in environment variables — never hardcoded or in config files
- [ ] `SUPABASE_SERVICE_ROLE_KEY` in GitHub Secrets — never in `.env` committed to repo
- [ ] `JWT_SECRET` rotated at least quarterly — rotation procedure documented in RUNBOOK.md
- [ ] `.env` files in `.gitignore` — verify with: `git log --all -- "**/.env"`
- [ ] Gitleaks runs in CI on every push — no secrets in git history

### Container Security
```dockerfile
# Always use pinned digest, not tags
FROM python:3.12.3-slim@sha256:<digest>

# Never run as root
RUN useradd --create-home --no-log-init appuser
USER appuser

# Minimal filesystem — no package managers in production layer
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
```

### Network Security
- [ ] Supabase RLS enabled on all tenant tables — verify with Prahari's audit query
- [ ] CORS `allow_origins` is explicit list — never `["*"]` in production
- [ ] No debug endpoints (`/docs`, `/redoc`, `/openapi.json`) accessible publicly in prod
- [ ] Rate limiting at nginx/proxy layer — not just application layer

### Access Control
- [ ] GitHub Actions secrets scoped to environments (production vs staging)
- [ ] Supabase service role key not accessible to frontend — backend only
- [ ] Database backup access restricted to ops team only
- [ ] Log aggregation service has read-only keys — no write access to application infra

### Incident Response Runbook Entry
```markdown
## Runbook: Suspected Security Breach

### Severity: P1
### Estimated Time to Triage: 30 minutes

### Symptoms
- Unusual cross-tenant data access in logs
- Authentication failures spike
- Unexpected database queries from unknown IPs

### Immediate Actions
1. `supabase db reset-password` — rotate DB password
2. Rotate `JWT_SECRET` env var and redeploy — invalidates all sessions
3. Rotate `SUPABASE_SERVICE_ROLE_KEY` — revoke and reissue in Supabase dashboard
4. Review `agent_audit_log` for unusual agent activity in last 24h
5. Notify founder and Vishwa immediately

### Escalation
- Contact Prahari for post-incident security review
- File GitHub issue with `severity:critical` + `agent:prahari` label
```
