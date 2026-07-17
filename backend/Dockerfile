# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder
WORKDIR /app

# Install uv (pinned for reproducibility)
RUN pip install --no-cache-dir uv==0.5.0

# Copy dependency manifests first — maximise layer cache hits
COPY pyproject.toml uv.lock ./

# Sync production deps only; --no-editable avoids egg-link artefacts in venv
RUN uv sync --frozen --no-dev --no-editable

# ── Stage 2: production runtime ────────────────────────────────────────────────
FROM python:3.12-slim AS runtime
WORKDIR /app

# Security: non-root user/group (uid/gid 1001)
RUN groupadd --gid 1001 aethos && \
    useradd --uid 1001 --gid aethos --no-create-home --shell /sbin/nologin aethos

# Copy the pre-built venv from builder — no build tools in runtime image
COPY --from=builder /app/.venv /app/.venv

# Copy application source (app/ only — no tests, no dev tooling)
COPY app/ ./app/

# Deploy-time helpers: the opt-in migration applier + migration SQL. Used by the
# one-shot `migrate` compose service on hosts where the DB is reachable.
COPY scripts/ ./scripts/
COPY supabase/ ./supabase/

# Activate venv via PATH; disable .pyc generation and stdout buffering
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

USER aethos

EXPOSE 8080

# Liveness probe: hit /health with no auth
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8080}/health')"

# Cloud Run injects $PORT; default to 8080 for local docker run.
# 2 workers is safe for 2 vCPU Cloud Run instance; revisit after load tests.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 2 --log-level info"]
