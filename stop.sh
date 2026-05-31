#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# stop.sh — Stop Aethos PS local development servers
#
# Kills anything on ports 4200 (frontend) and 8010 (backend).
# ─────────────────────────────────────────────────────────────────────────────

BACKEND_PORT=8010
FRONTEND_PORT=4200

echo "Stopping Aethos PS dev servers (ports $FRONTEND_PORT, $BACKEND_PORT)..."

PIDS=$(lsof -t -i ":$FRONTEND_PORT" -i ":$BACKEND_PORT" 2>/dev/null || true)

if [ -n "$PIDS" ]; then
  echo "  Killing PIDs: $PIDS"
  echo "$PIDS" | xargs kill -9 2>/dev/null || true
  sleep 1
  echo "  ✓ Servers stopped."
else
  echo "  No servers found on ports $FRONTEND_PORT or $BACKEND_PORT."
fi
