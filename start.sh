#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start.sh — Aethos PS local development servers
#
# Frontend : http://localhost:4200  (ng serve with proxy to backend)
# Backend  : http://localhost:8010  (uvicorn --reload)
# Tunnel   : if cloudflared is configured, update its ingress to :4200/:8010
#
# Usage: ./start.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# The script lives at the root of the aethos-ps worktree.
# All paths are resolved relative to its own directory so it works
# regardless of where you invoke it from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# .env lookup order: repo root → backend/ subdirectory
if [ -f "$SCRIPT_DIR/.env" ]; then
  ENV_FILE="$SCRIPT_DIR/.env"
elif [ -f "$BACKEND_DIR/.env" ]; then
  ENV_FILE="$BACKEND_DIR/.env"
else
  echo "ERROR: .env not found in $SCRIPT_DIR or $BACKEND_DIR"
  echo "Copy backend/.env.example, fill in secrets, and save as .env"
  exit 1
fi

BACKEND_PORT=8010
FRONTEND_PORT=4200
WORKER_QUEUES="default,extractions,billing,fx"

# Stop any existing dev servers first
"$SCRIPT_DIR/stop.sh" 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║        Aethos PS — Local Dev Startup             ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Backend ──────────────────────────────────────────────────────────────────
echo "▶ Starting backend on :$BACKEND_PORT ..."
echo "  Env file: $ENV_FILE"

(
  cd "$BACKEND_DIR"
  set -a
  [ -f "$ENV_FILE" ] && source "$ENV_FILE"
  set +a
  nohup uv run uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --reload \
    --log-level info \
    > /tmp/aethos-backend.log 2>&1
) &

# Wait for backend to be ready (up to 30s)
echo -n "  Waiting for backend"
for i in $(seq 1 30); do
  if curl -sf "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
    echo " ✓ ready"
    break
  fi
  echo -n "."
  sleep 1
done

# ── Procrastinate worker ─────────────────────────────────────────────────────
# Start background job worker (document extraction, billing-runs, FX refresh).
# Skipped gracefully if DATABASE_URL is not set (inline sync mode still works).
# Check if DATABASE_URL is set AND is reachable (some Supabase projects are IPv6-only which
# requires the Supabase IPv4 add-on or the pooler URL from Dashboard → Settings → Database)
DB_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"'"'" | xargs)
DB_REACHABLE=false
if [ -n "$DB_URL" ]; then
  # Quick connectivity check (3s timeout)
  if python3 -c "
import psycopg, os, sys, re
url = '''$DB_URL'''
try:
    conn = psycopg.connect(url, connect_timeout=3)
    conn.close()
    sys.exit(0)
except: sys.exit(1)
" 2>/dev/null; then
    DB_REACHABLE=true
  fi
fi

if [ "$DB_REACHABLE" = "true" ]; then
  echo "▶ Starting Procrastinate worker ..."
  (
    cd "$BACKEND_DIR"
    set -a
    [ -f "$ENV_FILE" ] && source "$ENV_FILE"
    set +a
    nohup uv run python -m procrastinate \
      --app=app.workers.procrastinate_app.app \
      worker \
      --queues="$WORKER_QUEUES" \
      --concurrency=2 \
      > /tmp/aethos-worker.log 2>&1
  ) &
  echo "  ✓ Worker started  (logs: tail -f /tmp/aethos-worker.log)"
else
  if [ -n "$DB_URL" ]; then
    echo "  ⚠ Worker skipped — DATABASE_URL set but DB unreachable"
    echo "    Likely cause: Supabase project is IPv6-only. Fix options:"
    echo "    1. Dashboard → Settings → Database → Connection string → copy pooler URL"
    echo "    2. Enable Supabase IPv4 add-on (\$4/month)"
    echo "    Inline sync extraction continues to work normally."
  else
    echo "  ⚠ Skipping worker — DATABASE_URL not set (inline sync extraction active)"
  fi
fi

# ── Frontend ─────────────────────────────────────────────────────────────────
echo "▶ Starting frontend on :$FRONTEND_PORT ..."
(
  cd "$FRONTEND_DIR"
  # Update proxy target to point at the dev backend port
  PROXY_CONF='{"\/api":{"target":"http://localhost:'"$BACKEND_PORT"'","secure":false,"changeOrigin":true,"logLevel":"warn"},"\/health":{"target":"http://localhost:'"$BACKEND_PORT"'","secure":false,"changeOrigin":true}}'
  echo "$PROXY_CONF" > proxy.conf.dev.json
  nohup npx ng serve \
    --host 0.0.0.0 \
    --port "$FRONTEND_PORT" \
    --proxy-config proxy.conf.dev.json \
    > /tmp/aethos-frontend.log 2>&1
) &

# Wait for frontend (up to 60s)
echo -n "  Waiting for frontend"
for i in $(seq 1 60); do
  if curl -sf "http://localhost:$FRONTEND_PORT/" > /dev/null 2>&1; then
    echo " ✓ ready"
    break
  fi
  echo -n "."
  sleep 1
done

echo ""
echo "┌──────────────────────────────────────────────────┐"
echo "│  Aethos PS is running                            │"
echo "│  Frontend : http://localhost:$FRONTEND_PORT              │"
echo "│  Backend  : http://localhost:$BACKEND_PORT              │"
echo "│  Worker   : Procrastinate (background)           │"
echo "│  Logs     : tail -f /tmp/aethos-backend.log      │"
echo "│             tail -f /tmp/aethos-frontend.log     │"
echo "│             tail -f /tmp/aethos-worker.log       │"
echo "│  Stop     : ./stop.sh                            │"
echo "└──────────────────────────────────────────────────┘"
echo ""
