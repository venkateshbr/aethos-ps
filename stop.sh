#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# stop.sh — Stop Aethos PS local development servers
#
# Kills anything on ports 4200 (frontend) and 8010 (backend).
# ─────────────────────────────────────────────────────────────────────────────

BACKEND_PORT=8010
FRONTEND_PORT=4200

echo "Stopping Aethos PS dev servers (ports $FRONTEND_PORT, $BACKEND_PORT)..."

# Kill processes on the two HTTP ports (backend + frontend)
PIDS=$(lsof -t -i ":$FRONTEND_PORT" -i ":$BACKEND_PORT" 2>/dev/null || true)

if [ -n "$PIDS" ]; then
  echo "  Killing PIDs: $PIDS"
  echo "$PIDS" | xargs kill -9 2>/dev/null || true
  sleep 1
  echo "  ✓ Servers stopped."
else
  echo "  No servers found on ports $FRONTEND_PORT or $BACKEND_PORT."
fi

# Kill Procrastinate worker (identified by the module name)
WORKER_PIDS=$(pgrep -f "procrastinate.*worker" 2>/dev/null || true)
if [ -n "$WORKER_PIDS" ]; then
  echo "  Stopping Procrastinate worker..."
  echo "$WORKER_PIDS" | xargs kill -9 2>/dev/null || true
  echo "  ✓ Worker stopped."
fi
