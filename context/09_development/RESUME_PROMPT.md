# Resume prompt

Paste this into a new Claude Code session opened on branch `claude/project-thread-2p04se` of
`crismag/realestate_marketing_crm` (or run `claude --continue` in the same checkout):

---

You are resuming the autonomous CRM build `autonomous-build-2026-11-12`. The fixed deadline is
2026-11-13T07:08:03Z; do not extend it. If it has passed, do only handoff and verification work.

1. Read `CLAUDE.md`, `context/09_development/AUTONOMOUS_RUN_STATE.json`, `context/09_development/RUN_LOG.md`
   (last rows) and `docs/REQUIREMENTS_MATRIX.md`.
2. Recreate the environment: `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
3. Re-run the evidence before trusting it: `.venv/bin/python -m pytest -p no:logging`, `.venv/bin/ruff check .`,
   and `scripts/e2e.sh` if Playwright is available. Record results; never mark a check passed without running it.
4. Continue from `next_action` in the state file. Keep the boundaries: implementation defaults are not
   approvals; sandbox transport only; no deployment, purchases, real customer data or messages; no
   force-push; preserve ADR-001/002 and the product exclusions.
5. After each slice: commit, push, update the state file and append a RUN_LOG row with UTC time and evidence.

---
