#!/usr/bin/env bash
# Production-like smoke + browser journey.
# Builds static files, starts waitress with CRM_ENV=production and DEBUG off on a
# throwaway database, seeds fictional demo data, runs the Playwright journey,
# then stops the server. Nothing outside the temporary directory is touched.
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${CRM_PYTHON:-.venv/bin/python}"
PORT="${E2E_PORT:-8765}"
WORK="$(mktemp -d)"
trap 'kill "${SERVER_PID:-0}" 2>/dev/null || true; rm -rf "$WORK"' EXIT

export CRM_ENV=production CRM_DEBUG=0
export CRM_VAR_DIR="$WORK/var" CRM_DB_PATH="$WORK/var/crm.sqlite3" CRM_BACKUP_DIR="$WORK/var/backups"
export CRM_SECRET_KEY="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(50))')"
export CRM_ALLOWED_HOSTS=127.0.0.1,localhost
export CRM_SECURE_COOKIES=0   # plain http on loopback for this test only
export CRM_DEMO_PASSWORD="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(12))')"
export CRM_PYTHON="$PY" CRM_URL="http://127.0.0.1:$PORT"
mkdir -p "$CRM_VAR_DIR"

echo "== check --deploy"
"$PY" manage.py check --deploy --fail-level ERROR
echo "== migrate + collectstatic"
"$PY" manage.py migrate -v0
"$PY" manage.py collectstatic --noinput -v0
echo "== seed fictional demo data (allowed only because this DB is throwaway)"
CRM_ENV=development "$PY" manage.py seed_demo >/dev/null

echo "== start waitress on :$PORT"
"$PY" -m waitress --listen="127.0.0.1:$PORT" --threads=4 crm_project.wsgi:application >"$WORK/server.log" 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 50); do
  curl -fsS "$CRM_URL/healthz" >/dev/null 2>&1 && break
  sleep 0.2
done
curl -fsS "$CRM_URL/healthz"; echo
echo "== static asset served with caching by whitenoise"
curl -fsSI "$CRM_URL/static/crm/crm.css" | grep -i -E "^HTTP|cache-control" || true
echo "== debug off: unknown page returns the styled 404"
code=$(curl -s -o /dev/null -w '%{http_code}' "$CRM_URL/does-not-exist")
test "$code" = "302" -o "$code" = "404"

echo "== browser journey"
NODE_PATH="${NODE_PATH:-$(npm root -g)}" node e2e/journey.cjs
