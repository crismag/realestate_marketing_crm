#!/usr/bin/env bash
# Idempotent dependency preparation for Cursor-hosted builds; no runtime data or credentials.
set -euo pipefail
cd "$(dirname "$0")/.."
CRM_SETUP_PYTHON="${CRM_SETUP_PYTHON:-python3}"
"$CRM_SETUP_PYTHON" -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12+ required (3.13 preferred)"'
command -v node >/dev/null
command -v npm >/dev/null
node -e 'if (Number(process.versions.node.split(".")[0]) < 22) throw new Error("Node 22+ required")'
if [[ ! -x .venv/bin/python ]]; then
  "$CRM_SETUP_PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install -r requirements-dev.txt
npm ci --prefix e2e --no-audit --no-fund
e2e/node_modules/.bin/playwright install --with-deps chromium
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
