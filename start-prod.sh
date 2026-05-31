#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start-prod.sh — Aethos PS production Docker build + launch
#
# Builds and starts two containers:
#   aethos-ps-api       → backend  at http://localhost:8011
#   aethos-ps-frontend  → frontend at http://localhost:4301
#
# Prerequisites:
#   - Docker Desktop (or Docker Engine) running
#   - .env file at the repo root (copy from backend/.env.example and fill in)
#   - STRIPE_*, SUPABASE_*, OPENROUTER_API_KEY, etc. must be set
#
# Usage: ./start-prod.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREE="$REPO_ROOT/.claude/worktrees/compassionate-merkle-90c923"
ENV_FILE="$WORKTREE/backend/.env"

BACKEND_PORT=8011
FRONTEND_PORT=4301

# Resolve the env file — prefer worktree-specific, fall back to repo root
if [ -f "$WORKTREE/.env" ]; then
  ENV_FILE="$WORKTREE/.env"
elif [ -f "$REPO_ROOT/.env" ]; then
  ENV_FILE="$REPO_ROOT/.env"
elif [ -f "$WORKTREE/backend/.env" ]; then
  ENV_FILE="$WORKTREE/backend/.env"
else
  echo "ERROR: .env not found. Copy backend/.env.example, fill in secrets, and place it at the repo root."
  exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║      Aethos PS — Production Docker Launch        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Env file : $ENV_FILE"
echo "  Backend  : http://localhost:$BACKEND_PORT"
echo "  Frontend : http://localhost:$FRONTEND_PORT"
echo ""

# Stop any existing containers
"$REPO_ROOT/stop-prod.sh" 2>/dev/null || true

# Build + start
echo "▶ Building Docker images (this may take a few minutes on first run)..."
docker compose \
  -f "$WORKTREE/infra/docker-compose.prod.yml" \
  --project-directory "$WORKTREE" \
  --env-file "$ENV_FILE" \
  --project-name aethos-ps \
  up --build -d

echo ""
echo "▶ Waiting for containers to be healthy..."
for i in $(seq 1 60); do
  API_STATUS=$(docker inspect --format='{{.State.Health.Status}}' aethos-ps-api 2>/dev/null || echo "starting")
  if [ "$API_STATUS" = "healthy" ]; then
    echo "  ✓ Backend healthy"
    break
  fi
  echo -n "."
  sleep 2
done
echo ""

echo "┌──────────────────────────────────────────────────┐"
echo "│  Aethos PS (prod) is running                     │"
echo "│  Frontend : http://localhost:$FRONTEND_PORT              │"
echo "│  Backend  : http://localhost:$BACKEND_PORT              │"
echo "│  Logs     : docker logs -f aethos-ps-api         │"
echo "│             docker logs -f aethos-ps-frontend    │"
echo "│  Stop     : ./stop-prod.sh                       │"
echo "└──────────────────────────────────────────────────┘"
echo ""

# Tunnel note — cloudflared config points at 4201/8011.
# If you want the tunnel to route to these prod containers, update
# ~/.cloudflared/config.yml ingress to point at localhost:4301 / localhost:8011.
echo "  ⚠ Cloudflare tunnel: if aethos-dev/aethos-api point at :4201/:8011,"
echo "    update ~/.cloudflared/config.yml ingress to :$FRONTEND_PORT/:$BACKEND_PORT"
echo "    and restart cloudflared."
echo ""
