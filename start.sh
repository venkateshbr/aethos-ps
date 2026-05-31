#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start.sh — Aethos PS local development servers
#
# Frontend : http://localhost:4300  (ng serve with proxy to backend)
# Backend  : http://localhost:8010  (uvicorn --reload)
# Tunnel   : if cloudflared is configured, update its ingress to :4300/:8010
#
# Usage: ./start.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREE="$REPO_ROOT/.claude/worktrees/compassionate-merkle-90c923"
BACKEND_DIR="$WORKTREE/backend"
FRONTEND_DIR="$WORKTREE/frontend"
ENV_FILE="$REPO_ROOT/.claude/worktrees/intelligent-saha-9ad2e3/backend/.env"

BACKEND_PORT=8010
FRONTEND_PORT=4300

# Stop any existing dev servers first
"$REPO_ROOT/stop.sh" 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║        Aethos PS — Local Dev Startup             ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Backend ──────────────────────────────────────────────────────────────────
echo "▶ Starting backend on :$BACKEND_PORT ..."
if [ ! -f "$ENV_FILE" ]; then
  echo "  ⚠ .env not found at $ENV_FILE — backend may fail to start"
fi

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
echo "│  Logs     : tail -f /tmp/aethos-backend.log      │"
echo "│             tail -f /tmp/aethos-frontend.log     │"
echo "│  Stop     : ./stop.sh                            │"
echo "└──────────────────────────────────────────────────┘"
echo ""
