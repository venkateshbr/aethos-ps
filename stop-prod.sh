#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# stop-prod.sh — Stop Aethos PS production Docker containers
#
# Tears down the aethos-ps-api and aethos-ps-frontend containers.
# Does NOT remove the built images (use --rmi all to also purge images).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREE="$REPO_ROOT/.claude/worktrees/compassionate-merkle-90c923"
ENV_FILE="${WORKTREE}/backend/.env"
[ -f "$REPO_ROOT/.env" ] && ENV_FILE="$REPO_ROOT/.env"

echo "Stopping Aethos PS production containers..."

docker compose \
  -f "$WORKTREE/infra/docker-compose.prod.yml" \
  --project-directory "$WORKTREE" \
  --env-file "$ENV_FILE" \
  --project-name aethos-ps \
  down 2>/dev/null || true

echo "  ✓ Containers stopped."
