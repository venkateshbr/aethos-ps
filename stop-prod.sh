#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# stop-prod.sh — Stop Aethos PS production Docker containers
#
# Tears down the aethos-ps-api and aethos-ps-frontend containers.
# Does NOT remove the built images (use --rmi all to also purge images).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/backend/.env"
[ -f "$SCRIPT_DIR/.env" ] && ENV_FILE="$SCRIPT_DIR/.env"

echo "Stopping Aethos PS production containers..."

docker compose \
  -f "$SCRIPT_DIR/infra/docker-compose.prod.yml" \
  --project-directory "$SCRIPT_DIR" \
  --env-file "$ENV_FILE" \
  --project-name aethos-ps \
  down 2>/dev/null || true

echo "  ✓ Containers stopped."
