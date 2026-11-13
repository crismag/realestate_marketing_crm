# Cursor-hosted environment and launch

## One-time account setup
1. Open https://cursor.com/agents (or choose Cloud under Cursor's agent input).
2. Connect the GitHub account with read/write access to `crismag/realestate_marketing_crm`.
3. Select that repository and the branch containing this handoff; after merge, updated main is sufficient. Use Cursor-hosted execution, not a local/self-hosted runner.
4. Select/create a cloud environment. Verify its active configuration uses the committed `.cursor/environment.json` or explicitly set the install command to `bash scripts/cursor-cloud-setup.sh`.
5. Prepare Python 3.13 (3.12 minimum), Node 22+, npm, Python venv support and Ubuntu browser dependencies. Use Cursor's guided setup to resolve missing OS packages. Let the environment Build complete successfully; inspect logs instead of assuming the repo config was applied.
6. Paste MASTER_PROMPT.md and start the agent. Set any desired usage budget in Cursor account controls; this handoff does not choose or raise a spend limit.

Cloud execution uses a Git checkout inside the remote VM; it does not work without a filesystem. The distinction is that your laptop's working copy and uptime are unnecessary. GitHub remains the durable source.

## Dependency preparation
```
bash scripts/cursor-cloud-setup.sh
```
This idempotently installs pinned Python and Node dependencies and Playwright Chromium, then checks Django/migration consistency. It intentionally does not seed a database, create credentials or start services in a Build. No production secret is needed for baseline unit tests. OS dependencies for Playwright may need the cloud setup agent's package-install permissions.

Cursor saved personal/team environment settings can take precedence over the repository file. Verify which environment and successful Build the run actually used. Do not mistake an old cached Build for proof that a new install script ran.

## Start a disposable cloud preview
From the cloud repo root, in a runtime terminal (not the Build install step):
```
export CRM_ENV=development
export CRM_VAR_DIR="$PWD/var/cursor-preview"
export CRM_DB_PATH="$CRM_VAR_DIR/crm.sqlite3"
mkdir -p "$CRM_VAR_DIR"
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver 0.0.0.0:8000
```
Use `seed_demo` only for the fresh fictional preview. Reuse its existing state on later starts; do not overwrite real data or assume the seed is idempotent. Demo credentials remain in the private run terminal; do not commit or paste passwords into PRs.

In a second cloud terminal, use the same exports and run:
```
.venv/bin/python manage.py run_worker
```
Use Cursor's forwarded port/preview for port 8000. Keep development previews access controlled and fictional. Both web and worker must share the preview DB; parallel agents/tests must use their own DBs. This preview is not production hosting.

Settings are environment variables; `.env` is not automatically loaded by this app. Persistent disks/Builds preserve files, not running services or shell exports; restart runtime services explicitly.

## Verification and troubleshooting
```
CRM_TEST_DB_PATH=/tmp/crm-cloud-baseline.sqlite3 .venv/bin/python -m pytest -p no:logging
.venv/bin/ruff check .
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/pip-audit -r requirements.txt
NODE_PATH=e2e/node_modules bash scripts/e2e.sh
```
`scripts/e2e.sh` uses a temporary database, seeds fictional data, runs a production-like server and checks desktop/mobile flows. It cleans its own runtime server. `CRM_CHROMIUM_PATH` can select an already installed compatible Chromium. A browser launch/download failure must be reported separately from application failures; try the documented environment setup once, then use hosted CI when available. Do not disable browser/security assertions to manufacture a pass.

If the optional Docker deployment drill is selected, check Docker availability first. Inspect `deploy/`, `scripts/new_company.sh` and the install guide; run only disposable internal tests. Do not create public DNS/TLS endpoints or publish a production instance under this handoff.

## Cloud secrets and networking
Use Cursor's environment secret controls for any later credentials. Do not upload local .env files, account tokens, production databases or encryption keys into Build snapshots. Baseline development uses sandbox transport. A real provider is a separate dependent stage.

Setup needs access to GitHub, the configured Python package registry, npm registry and Playwright browser distribution endpoints; determine actual endpoints from successful installation logs rather than opening arbitrary networks. Application integration endpoints should be added only for the selected task.

## Documentation checked 13 November 2026
- https://cursor.com/docs/cloud-agent — cloud VM, provider connection, web/Desktop entry and branch/PR model.
- https://cursor.com/docs/cloud-agent/setup — install configuration, Build/runtime separation and saved environment precedence.

The package configuration uses only the documented `install` field; no speculative model/runtime/keepalive keys are included. Account setup, successful Cursor Build and an actual Cursor run have not been performed from ChatGPT.
