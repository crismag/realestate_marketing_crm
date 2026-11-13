# Resume prompt — 2026-11-13T02:36Z run

Continue the Real Estate CRM on branch `cursor/sales-board-crisgen-behaviors-77d9` (or main after it merges).
Read CLAUDE.md, `context/09_development/AUTONOMOUS_RUN_STATE.json` and `docs/KNOWN_LIMITATIONS.md`.
The fixed window is 2026-11-13T02:36:00Z to 2026-11-13T14:36:00Z. Do not extend it. Do not rebuild TASK-003–011.

Verified on this branch: sales list/board, filter drawer, stage-move modal (`static/crm/behaviors.js`),
203 pytest, ruff, and `scripts/e2e.sh` (19 checks, including 390px). Stage moves do not change the handler or lifecycle.
Sandbox email stays labelled not sent.

Next in-scope gap, in order: hosted CI for this branch; then either staff digest email through the existing staff-mail path (never a customer send) or a retention/deletion workflow. Bulk responsibility changes must stay handovers (ADR-001/002). Do not mark open decisions approved. Do not load Material Dashboard CSS. Do not edit `crm/core/static/vendor/crisgen-ui/`.

Verify with pytest, ruff, `makemigrations --check --dry-run`, and `scripts/e2e.sh` when templates, CSS or flows change. Append `context/09_development/RUN_LOG.md`.
