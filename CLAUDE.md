# CLAUDE.md

Guidance for coding agents working in this repository.

## What this is

An internal real estate sales/marketing CRM: Django 5.2 LTS, server-rendered templates, SQLite (WAL),
a database-backed job worker, CrisGen UI 1.1 (vendored CSS). Requirements and decisions live in
`context/`; start with `context/README.md` and `context/04_requirements/OPEN_DECISIONS.md`.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python manage.py migrate && .venv/bin/python manage.py seed_demo   # fresh DB only
.venv/bin/python manage.py runserver            # web
.venv/bin/python manage.py run_worker           # background jobs (separate process)
.venv/bin/python -m pytest -p no:logging        # all tests (~10 s)
.venv/bin/ruff check .                          # lint
scripts/e2e.sh                                  # production-like smoke + Playwright journey (needs playwright)
```

## Rules that must not be broken

- **ADR-001**: the sender stays responsible until the recipient accepts a handover.
- **ADR-002**: claims are atomic and exclusive; release to a pool needs coordinator acceptance; overdue work
  never removes ownership automatically.
- One workspace; every signed-in user sees every customer. Do not add role-based record restrictions,
  customer portals, tenancy, payout accounting or property inventory.
- Customer-facing email goes through the **sandbox** transport by default and is labelled "not sent".
  Never label sandbox captures as deliveries. Never send real customer messages from tests or demos.
- Implementation defaults are not business approvals. Keep them configurable and listed in
  `docs/IMPLEMENTATION_DEFAULTS.md`; never mark open decisions as approved.
- No fixed passwords, committed secrets, `.env` files or databases with personal data.

## How the code is organised

- Business logic lives in `crm/<app>/services.py`; views stay thin and call services through
  `crm.core.web.run_action` (which maps `DomainError`/`ConflictError`/`NotAllowed` to messages).
- Every consequential change: run inside `crm.core.db.write_transaction`, write an `audit(...)` row in the
  same transaction, and `emit(...)` an outbox event if automation should react.
- Concurrency: optimistic `version` fields with conditional `UPDATE … WHERE version=n`; idempotency via
  unique keys (`operation_key`, `logical_key`, `external_key`). Keep it portable to MySQL (no partial
  indexes, no `SKIP LOCKED`).
- Time: always `crm.core.clock.now()` (tests freeze it with `clock.frozen(...)`). Store UTC; display in the
  workspace timezone.
- Policy values come from `crm.core.services.get_policy()`; defaults in `crm/core/policy.py`.
- Attention is derived at read time in `crm/attention/services.py`; do not store "needs attention" flags.
- Worker jobs must be idempotent and must not hold a write transaction across slow work.

## UI

- Use CrisGen UI classes from `crm/core/static/vendor/crisgen-ui/components.css` (never edit vendored files).
  Layout goes in `static/crm/crm.css` using CrisGen tokens. See `docs/UI_COMPONENTS.md` for the map and gaps.
- CSP forbids inline `style=` and inline scripts; `tests/test_web.py` enforces it.
- Pages must not scroll sideways at 390px (checked by `e2e/journey.cjs`).

## Before you push

Run pytest and ruff; run `scripts/e2e.sh` when templates, CSS or flows change. Update
`docs/REQUIREMENTS_MATRIX.md` when you add or change behaviour, and append to
`context/09_development/RUN_LOG.md`.
