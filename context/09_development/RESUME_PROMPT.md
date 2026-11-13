# Resume prompt — 2026-11-13T02:36Z run

Continue the Real Estate CRM on branch `cursor/sales-board-crisgen-behaviors-77d9` (or main after it merges).
Read CLAUDE.md, `context/09_development/AUTONOMOUS_RUN_STATE.json` and `docs/KNOWN_LIMITATIONS.md`.
The fixed window is 2026-11-13T02:36:00Z to 2026-11-13T14:36:00Z. Do not extend it. Do not rebuild TASK-003–011.

Verified on this branch: sales list/board with the review fixes, a staff-only daily digest copy, and an explained attention priority score (C-R1).
226 pytest, ruff, and `scripts/e2e.sh` when the score templates were checked.
A stage move keeps the posted outcome filter, refuses a stale version, and does not change the handler or lifecycle.
The digest copy uses staff mail (file folder, or SMTP when configured). It is not a customer message. Sandbox customer email stays labelled not sent.
The priority score sorts inside the existing severity groups. Turning it off restores age order. It does not rank people or change who is responsible. The weights are an implementation default.

The isolated SQLite restore, the keyboard and contrast pass on this run's screens, and the new-slice security checks are recorded in the run log at 2026-11-13T03:18:40Z. Do not repeat them. Remaining gaps are outside this build: a real customer email provider, a live MySQL database, a public deploy, and a pass with the sales team. Do not build retention, a calendar, saved filters, or bulk handovers unless a requirement requires them. Bulk responsibility changes must stay handovers (ADR-001/002). Do not mark open decisions approved. Do not load Material Dashboard CSS. Do not edit `crm/core/static/vendor/crisgen-ui/`.

Verify with pytest, ruff, `makemigrations --check --dry-run`, and `scripts/e2e.sh` when templates, CSS or flows change. Append `context/09_development/RUN_LOG.md`.
