# Current development run — 13 November 2026

Checkpoint UTC: 2026-11-13T01:33:17.914540+00:00. Branch: `codex/crm-development-hardening-20261113`. Base: `add45d03c1224c9651ed0bf6e4f049761c26bfe3`. The containing commit is identified by Git history; no self-referential commit SHA is embedded.

## Outcome
Continued the existing CRM with four specialist agents and a coordinating implementer/reviewer. Fixed verified correctness defects, closed two required attention/digest gaps, and replaced stale documentation-only entry points with current execution context. This is an implementation hardening release candidate, not production deployment or pilot acceptance.

## Changes
- Fenced worker completion and lease recovery by owner, running state, attempt and recovery expiry snapshot; obsolete workers cannot finalize newer work or fail its message.
- Preserved original inquiry stop conditions on manual message retries. Stale transitions conflict; each successful retry gets a unique generation; missing originating context blocks unsafe retry.
- Rejected future inquiries and human responses dated before their inquiries. Historical capture and idempotent replays remain supported.
- Made reporting spend and its audit one atomic service operation.
- Added response-needed attention for inbound replies without inquiries; later human-response evidence clears it. Agreed future contact pauses tour cadence without hiding urgent work.
- Added migration `automation.0003_digest_snapshots` and durable per-user/day snapshots. Digest reports new/continuing/resolved unique clients against the prior delivered digest, including resolved-only days; replay does not rewrite the baseline.
- Updated context entry points, handoff/resume, model checkpoint, requirement evidence and limits. Enabled CI push checks on codex branches and system Chromium selection for browser tests; committed npm lockfile.

## Fresh verification
| Check | Observed result |
|---|---|
| Baseline pytest / Ruff | 94 passed; lint passed before edits |
| Final `CRM_TEST_DB_PATH=/tmp/root-crm-release.sqlite3 .venv/bin/python -m pytest -p no:logging` | 127 passed in 10.71s |
| `.venv/bin/ruff check .` | All checks passed |
| `.venv/bin/python manage.py check` | No issues |
| `.venv/bin/python manage.py makemigrations --check --dry-run` | No changes detected |
| `.venv/bin/pip-audit -r requirements.txt` | No known vulnerabilities found |
| `node --check e2e/journey.cjs`, `git diff --check` | Passed |
| Regression RED → GREEN | Observed by assigned agents; coordinator directly observed tour-agreement regression failure then pass |
| Production-like smoke | Migration, collectstatic, fictional seed, worker, HTTP health/static checks completed before browser launch |
| Browser journey | Blocked: Playwright browser download returned invalid archive; system Chromium aborts with socket Operation not permitted. No fresh browser pass claimed |
| TLS production `check --deploy --fail-level WARNING` | Two warnings: HSTS include-subdomains and preload remain disabled. These require actual domain-wide TLS decisions, not automatic enablement |

## Operational upgrade
Back up and stop web/worker before normal upgrade. Run `.venv/bin/python manage.py migrate`, then restart both supervised processes. New digest baselines begin with the first post-upgrade digest. Customer messages remain local sandbox captures.

## Remaining work and precise limitations
- Fresh browser journeys on a host that permits Chromium; sales-team usability and assistive-technology review.
- Hosting/TLS, storage encryption, durable backup destination and target-environment restore drill.
- Real email provider/sender credentials and signed delivery callbacks only if live customer email is selected.
- MySQL validation remains deferred as requested; no MySQL server tested.
- Reply response matching is chronological per contact rather than explicit reply-thread linkage. Unlinked inquiry/reply identity cannot be inferred; unique-contact totals still deduplicate.
- Digest resolution means departure from the recipient's queue, including reassignment; transient states between deliveries are not reconstructed.
- Representative-volume load tests and optional product backlog in docs/KNOWN_LIMITATIONS.md remain open. Configurable business defaults are not silently marked approved.

## Continuation
Read DEVELOPMENT_EXECUTION.md, CLAUDE.md and this report. Prioritize fresh browser/pilot validation, remediate observed defects, then implement only in-scope backlog. Use isolated test database paths for concurrent agents. Historical autonomous-run deadlines do not constrain this new assignment. No unattended runtime is left running by this run.

## Hosted verification and publication

Published code commit: `bd49e603bc976547cc7a5b27485d9906000cad1a` (tree exactly matched the locally verified tree). Draft PR: https://github.com/crismag/realestate_marketing_crm/pull/4. GitHub CI run https://github.com/crismag/realestate_marketing_crm/actions/runs/43345965197 completed successfully, including lint, Django/migration checks, automated tests, dependency audit and the production-like browser journey at desktop and 390px. This closes the fresh browser verification gap above; only the local environment remains unable to launch Chromium. This evidence applies to the code commit; the subsequent checkpoint commit changes documentation only.

Pilot acceptance, hosting, actual provider integration, team usability/accessibility and scale validation remain open as described above.
