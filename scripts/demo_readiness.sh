#!/usr/bin/env bash
# Demo readiness runner for Aethos PS.
#
# Usage:
#   DEMO_TENANT_ID=<tenant-uuid> make demo-ready
#
# Optional:
#   AETHOS_PS_API_URL=http://localhost:8011
#   AETHOS_PS_WEB_URL=http://localhost:4201
#   AETHOS_TS_WEB_URL=http://localhost:4202
#   DEMO_E2E_SPECS="e2e/demo-v2-meridian.spec.ts e2e/r2r-reports-render.spec.ts"

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

AETHOS_PS_API_URL="${AETHOS_PS_API_URL:-http://localhost:8011}"
AETHOS_PS_WEB_URL="${AETHOS_PS_WEB_URL:-http://localhost:4201}"
AETHOS_TS_WEB_URL="${AETHOS_TS_WEB_URL:-http://localhost:4202}"
DEMO_E2E_SPECS="${DEMO_E2E_SPECS:-e2e/demo-v2-meridian.spec.ts}"

API_PORT="${AETHOS_PS_API_URL##*:}"
API_PORT="${API_PORT%%/*}"
WEB_PORT="${AETHOS_PS_WEB_URL##*:}"
WEB_PORT="${WEB_PORT%%/*}"

BACKEND_LOG="${TMPDIR:-/tmp}/aethos-demo-readiness-backend.log"
FRONTEND_LOG="${TMPDIR:-/tmp}/aethos-demo-readiness-frontend.log"

BACKEND_PID=""
FRONTEND_PID=""

usage() {
  cat <<'EOF'
Usage:
  DEMO_TENANT_ID=<tenant-uuid> make demo-ready

Required:
  DEMO_TENANT_ID       Existing tenant UUID to reset and seed.

Optional:
  AETHOS_PS_API_URL    Backend URL. Default: http://localhost:8011
  AETHOS_PS_WEB_URL    Frontend URL. Default: http://localhost:4201
  AETHOS_TS_WEB_URL    Timesheet URL. Default: http://localhost:4202
  DEMO_E2E_SPECS      Space-separated Playwright specs.
                       Default: e2e/demo-v2-meridian.spec.ts
EOF
}

cleanup() {
  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

if [ -z "${DEMO_TENANT_ID:-}" ]; then
  usage
  echo ""
  echo "ERROR: DEMO_TENANT_ID is required." >&2
  exit 2
fi

if [ -f "$ROOT_DIR/.env" ]; then
  ENV_FILE="$ROOT_DIR/.env"
elif [ -f "$BACKEND_DIR/.env" ]; then
  ENV_FILE="$BACKEND_DIR/.env"
else
  echo "ERROR: .env not found in $ROOT_DIR or $BACKEND_DIR" >&2
  exit 2
fi

wait_for_url() {
  local url="$1"
  local label="$2"
  local timeout="${3:-60}"
  local elapsed=0

  printf "Waiting for %s at %s" "$label" "$url"
  while [ "$elapsed" -lt "$timeout" ]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo " ready"
      return 0
    fi
    printf "."
    sleep 1
    elapsed=$((elapsed + 1))
  done

  echo ""
  echo "ERROR: $label did not become ready within ${timeout}s." >&2
  return 1
}

start_backend_if_needed() {
  if curl -fsS "$AETHOS_PS_API_URL/health" >/dev/null 2>&1; then
    echo "Backend already running at $AETHOS_PS_API_URL"
    return
  fi

  echo "Starting backend at $AETHOS_PS_API_URL"
  (
    cd "$BACKEND_DIR"
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
    uv run uvicorn app.main:app \
      --host 127.0.0.1 \
      --port "$API_PORT" \
      --log-level info
  ) >"$BACKEND_LOG" 2>&1 &
  BACKEND_PID="$!"

  wait_for_url "$AETHOS_PS_API_URL/health" "backend" 60 || {
    tail -80 "$BACKEND_LOG" >&2 || true
    exit 1
  }
}

start_frontend_if_needed() {
  if curl -fsS "$AETHOS_PS_WEB_URL/" >/dev/null 2>&1; then
    echo "Frontend already running at $AETHOS_PS_WEB_URL"
    return
  fi

  echo "Starting frontend at $AETHOS_PS_WEB_URL"
  (
    cd "$FRONTEND_DIR"
    npx ng serve \
      --host 127.0.0.1 \
      --port "$WEB_PORT" \
      --proxy-config proxy.conf.json
  ) >"$FRONTEND_LOG" 2>&1 &
  FRONTEND_PID="$!"

  wait_for_url "$AETHOS_PS_WEB_URL/" "frontend" 90 || {
    tail -120 "$FRONTEND_LOG" >&2 || true
    exit 1
  }
}

run_api_smoke() {
  echo "Running API smoke checks"
  curl -fsS "$AETHOS_PS_API_URL/health" >/dev/null
  curl -fsS "$AETHOS_PS_API_URL/api/v1/ping" >/dev/null
  curl -fsS "$AETHOS_PS_API_URL/health/ready" >/dev/null
}

seed_demo_tenant() {
  echo "Resetting and seeding demo tenant $DEMO_TENANT_ID"
  (
    cd "$BACKEND_DIR"
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
    uv run python -m scripts.seed_demo --tenant-id "$DEMO_TENANT_ID" --reset
  )
}

run_demo_e2e() {
  echo "Running selected Playwright demo specs: $DEMO_E2E_SPECS"
  (
    cd "$FRONTEND_DIR"
    AETHOS_PS_WEB_URL="$AETHOS_PS_WEB_URL" \
    AETHOS_PS_API_URL="$AETHOS_PS_API_URL" \
    AETHOS_TS_WEB_URL="$AETHOS_TS_WEB_URL" \
    npx playwright test $DEMO_E2E_SPECS --project=chromium --reporter=list
  )
}

echo "Aethos PS demo readiness"
echo "Backend:  $AETHOS_PS_API_URL"
echo "Frontend: $AETHOS_PS_WEB_URL"
echo "Tenant:   $DEMO_TENANT_ID"
echo "Specs:    $DEMO_E2E_SPECS"
echo ""

start_backend_if_needed
start_frontend_if_needed
seed_demo_tenant
run_api_smoke
run_demo_e2e

echo ""
echo "Demo readiness completed successfully."
