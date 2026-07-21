#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start-prod.sh — Aethos PS production Docker build + launch
#
# Builds and starts two containers:
#   aethos-ps-api       → backend  at http://localhost:8011
#   aethos-ps-frontend  → frontend at http://localhost:4201
#
# Prerequisites:
#   - Docker Desktop (or Docker Engine) running
#   - .env file at the repo root (copy from backend/.env.example and fill in)
#   - STRIPE_*, SUPABASE_*, OPENROUTER_API_KEY, etc. must be set
#
# Usage: ./start-prod.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKEND_PORT=8011
FRONTEND_PORT=4201
TIMESHEET_PORT=4202

# .env lookup order: same dir as script → backend/ subdirectory
if [ -f "$SCRIPT_DIR/.env" ]; then
  ENV_FILE="$SCRIPT_DIR/.env"
elif [ -f "$SCRIPT_DIR/backend/.env" ]; then
  ENV_FILE="$SCRIPT_DIR/backend/.env"
else
  echo "ERROR: .env not found in $SCRIPT_DIR or $SCRIPT_DIR/backend/"
  echo "Copy backend/.env.example, fill in secrets, and save as .env next to this script."
  exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║      Aethos PS — Production Docker Launch        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Env file  : $ENV_FILE"
echo "  Backend   : http://localhost:$BACKEND_PORT"
echo "  Frontend  : http://localhost:$FRONTEND_PORT"
echo "  Timesheet : http://localhost:$TIMESHEET_PORT"
echo ""

# Stop any existing containers
"$SCRIPT_DIR/stop-prod.sh" 2>/dev/null || true

# Build + start
echo "▶ Building Docker images (this may take a few minutes on first run)..."
AETHOS_ENV_FILE="$ENV_FILE" docker compose \
  -f "$SCRIPT_DIR/infra/docker-compose.prod.yml" \
  --project-directory "$SCRIPT_DIR" \
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
echo "│  Frontend  : http://localhost:$FRONTEND_PORT             │"
echo "│  Timesheet : http://localhost:$TIMESHEET_PORT             │"
echo "│  Backend   : http://localhost:$BACKEND_PORT             │"
echo "│  Worker    : aethos-ps-worker (background jobs)  │"
echo "│  Logs      : docker logs -f aethos-ps-api        │"
echo "│              docker logs -f aethos-ps-worker     │"
echo "│              docker logs -f aethos-ps-frontend   │"
echo "│              docker logs -f aethos-ps-timesheet  │"
echo "│  Stop      : ./stop-prod.sh                      │"
echo "└──────────────────────────────────────────────────┘"
echo ""
echo "  ⚠ Timesheet Portal tunnel: add a cloudflared ingress hostname"
echo "    (e.g. aethos-time.ishirock.com) → http://localhost:$TIMESHEET_PORT"
echo ""

# Tunnel note — cloudflared config points at 4201/8011.
# If you want the tunnel to route to these prod containers, update
# ~/.cloudflared/config.yml ingress to point at localhost:4201 / localhost:8011.
echo "  ⚠ Cloudflare tunnel: if aethos-dev/aethos-api point at :4201/:8011,"
echo "    update ~/.cloudflared/config.yml ingress to :$FRONTEND_PORT/:$BACKEND_PORT"
echo "    and restart cloudflared."
echo ""
