# Realstate CRM

An internal sales and marketing CRM for a real estate team: one shared workspace where every signed-in
colleague can see every customer, with clear responsibility, shared pools, accepted handovers, an
attention queue for forgotten clients, durable reminders, sandboxed customer email and reports that
reconcile to their source records.

Current autonomous development context and remaining stages: [`context/09_development/DEVELOPMENT_EXECUTION.md`](context/09_development/DEVELOPMENT_EXECUTION.md).

The product requirements live in [`context/`](context/README.md). This README covers running the software.

> Status: a locally runnable, tested build. It is **not production-ready**: see
> [Known limitations](docs/KNOWN_LIMITATIONS.md) before any pilot. Customer email uses a **local sandbox**
> that writes `.eml` files and sends nothing.

## Requirements

- Python 3.13 (3.12 works)
- SQLite 3.35+ (bundled with Python)
- Optional, for browser tests: Node 22 and Playwright 1.63 with Chromium

## Quick start (development)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env            # optional; every setting has a safe development default
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo          # fictional demo data; prints a one-time password
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

In a second terminal, run the background worker (reminders, digests, customer messages):

```bash
.venv/bin/python manage.py run_worker
```

Open http://127.0.0.1:8000 and sign in as `ana@demo.example.test` (agent), `cora@demo.example.test`
(pool coordinator), `max@demo.example.test` (manager) or `admin@demo.example.test` (administrator) with the
password `seed_demo` printed. Set `CRM_DEMO_PASSWORD` beforehand to choose it yourself. There is no fixed
default password anywhere.

Settings are read from environment variables (see [`.env.example`](.env.example)). The app does not load
`.env` by itself; export the variables or use your process manager's env file support.

### Without demo data

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py create_admin --email you@example.com      # prompts for a temporary password
```

The administrator must change the temporary password at first sign-in, then adds colleagues under
**Settings → People**.

## Everyday commands

| Task | Command |
|---|---|
| Run all automated tests (unit, integration, concurrency, worker restart, security, operations) | `.venv/bin/python -m pytest -p no:logging` |
| Lint | `.venv/bin/ruff check .` |
| Dependency audit | `.venv/bin/pip-audit -r requirements.txt` |
| Production-like smoke + browser journey (desktop and 390px) | `scripts/e2e.sh` |
| Process due jobs once and exit | `.venv/bin/python manage.py run_worker --once` |
| Run the attention sweep now | `.venv/bin/python manage.py run_worker --once --sweep-now` |
| Back up the database | `.venv/bin/python manage.py backup_db` |
| Verify a backup | `.venv/bin/python manage.py backup_db --verify var/backups/<file>.sqlite3` |
| Restore a backup (stop web + worker first) | `.venv/bin/python manage.py restore_db var/backups/<file>.sqlite3 --confirm <file>.sqlite3` |

`scripts/e2e.sh` needs Playwright: either a global install (`npm i -g playwright@1.63.0 && npx playwright install chromium`)
or `cd e2e && npm install && npx playwright install chromium`, then `NODE_PATH=e2e/node_modules scripts/e2e.sh`.

For an existing system Chromium, set `CRM_CHROMIUM_PATH=/usr/bin/chromium` when running the browser journey. Otherwise Playwright uses its downloaded browser.

## Production-like run

```bash
export CRM_ENV=production CRM_DEBUG=0
export CRM_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
export CRM_ALLOWED_HOSTS=crm.example.internal CRM_CSRF_TRUSTED_ORIGINS=https://crm.example.internal
export CRM_SECURE_COOKIES=1 CRM_SSL_REDIRECT=1 CRM_BEHIND_TLS_PROXY=1 CRM_HSTS_SECONDS=31536000
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python -m waitress --listen=127.0.0.1:8000 --threads=8 crm_project.wsgi:application
.venv/bin/python manage.py run_worker        # separate process; supervise both
```

Put a TLS-terminating reverse proxy in front. Run exactly one web process with several threads and one
worker process: SQLite allows one writer at a time, and this build is sized for a single office team.
See [Operations](docs/OPERATIONS.md) and [Security notes](docs/SECURITY.md).

## What is where

| Path | Contents |
|---|---|
| `crm/core` | Settings/policy, audit log, clock, DB helpers, security middleware, backup, Today and Settings screens |
| `crm/accounts` | Users (email sign-in), teams, login throttling, forced password change, user admin |
| `crm/contacts` | Contacts, inquiries, interactions, opportunities, watches, search, CSV export, intake API |
| `crm/work` | Responsibility (assignments), shared pools, claims, handovers, tasks |
| `crm/attention` | Attention evaluation, snoozes, follow-up coverage |
| `crm/automation` | Rules, durable job queue and worker, notifications, schedules |
| `crm/comms` | Customer email templates, sandbox transport, stop policies |
| `crm/reporting` | Declared metrics, reports, drill-downs, marketing spend |
| `templates/`, `static/crm/crm.css` | Server-rendered screens built from CrisGen UI 1.1 (vendored in `crm/core/static/vendor/crisgen-ui`) |
| `tests/` | pytest suites; `e2e/` browser journey; `scripts/e2e.sh` runner |
| `docs/` | Security, operations, MySQL migration, implementation defaults, requirement matrix, UI component map |

## Documentation

- [Implementation defaults](docs/IMPLEMENTATION_DEFAULTS.md): every product decision made during the build, all configurable
- [Requirement matrix](docs/REQUIREMENTS_MATRIX.md): requirement → implementation → test evidence
- [Security notes](docs/SECURITY.md)
- [Operations, backup and restore](docs/OPERATIONS.md)
- [Moving to MySQL](docs/MYSQL_MIGRATION.md)
- [UI component map (CrisGen UI)](docs/UI_COMPONENTS.md)
- [Known limitations and backlog](docs/KNOWN_LIMITATIONS.md)
