#!/usr/bin/env bash
# Synthetic test only. Fresh Docker network/containers, no app env or credentials.
set -euo pipefail
cd "$(dirname "$0")/.."
name="aethos-telegram-test-$$"
docker network create "$name" >/dev/null
cleanup() {
  docker rm -fv "$name-rest" "$name-db" >/dev/null 2>&1 || true
  docker network rm "$name" >/dev/null
}
trap cleanup EXIT

docker run -d --pull=never --name "$name-db" --network "$name" --network-alias db \
  -e POSTGRES_PASSWORD=telegram_fixture_only -e POSTGRES_DB=telegram_fixture \
  --mount "type=bind,src=$PWD/tests/fixtures/telegram_synthetic.sql,dst=/docker-entrypoint-initdb.d/01_fixture.sql,readonly" \
  --mount "type=bind,src=$PWD/supabase/migrations/0123_telegram_erp.sql,dst=/docker-entrypoint-initdb.d/02_telegram.sql,readonly" \
  postgres:17-alpine >/dev/null
for _ in $(seq 1 30); do
  if docker exec "$name-db" pg_isready -h 127.0.0.1 -U postgres -d telegram_fixture >/dev/null; then break; fi
  sleep 1
done
docker exec "$name-db" pg_isready -h 127.0.0.1 -U postgres -d telegram_fixture
docker run -d --pull=never --name "$name-rest" --network "$name" -p 127.0.0.1::3000 \
  -e PGRST_DB_URI=postgres://postgres:telegram_fixture_only@db:5432/telegram_fixture \
  -e PGRST_DB_ANON_ROLE=anon -e PGRST_DB_SCHEMAS=public \
  -e PGRST_JWT_SECRET=synthetic_jwt_key_for_fixture_only_0123456789abcdef \
  postgrest/postgrest:v14.8 >/dev/null
listen=$(docker port "$name-rest" 3000/tcp)
for _ in $(seq 1 30); do
  if curl -fsS "http://$listen/" >/dev/null 2>&1; then break; fi
  sleep 1
done
TELEGRAM_TEST_POSTGREST_PORT="${listen##*:}" uv run --locked pytest -q tests/test_telegram_synthetic_stack.py
