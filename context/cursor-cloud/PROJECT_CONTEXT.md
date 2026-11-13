# Full project context

## Product and intended users
An internal real estate team's shared sales and marketing workspace. Agents capture prospects, log tours/conversations, own follow-ups, claim shared-pool clients and hand over responsibility. Coordinators manage pools; managers see workload and sourced outcomes; administrators manage configuration and accounts. Every signed-in colleague can see customer records. Company setup is per installation, not a multi-tenant SaaS product.

A central requirement is preventing forgotten clients: surface toured clients without follow-up, unanswered inquiries/replies, overdue promises/tasks, inactivity, missing next actions, pending handovers and stalled opportunities. Explain each reason and who is accountable; count unique clients separately from overlapping reasons.

## Stack and runtime
Python 3.13 preferred / 3.12 supported; Django 5.2 LTS; SQLite WAL now; MySQL migration later. Server-rendered templates use vendored CrisGen UI 1.1. Waitress/WhiteNoise serve the app; a database-backed worker handles durable jobs, in-app notifications, sweeps and digests. Node 22 and pinned Playwright support browser tests. Docker/Compose/Caddy installation tooling exists. No stack rewrite or SPA migration is requested.

## Implemented at inspected main fda56b3
| Area | Current behavior / source |
|---|---|
| Identity | Email login, throttling, forced temporary-password change, password reset, TOTP two-step sign-in and recovery; `crm/accounts` |
| Customer relationships | Capture/search/filter, normalized duplicate suggestions, source/referral data, repeat inquiries, interaction history, lifecycle/opportunities/watches, token-auth intake; `crm/contacts` |
| Import/merge | CSV validation/preview/import and duplicate contact merge; `crm/contacts/importing.py`, `merging.py` |
| Responsibility/work | Exclusive pool claim, accepted transfer/release, history, tasks/promises, departed-colleague handling; `crm/work` |
| Attention | Derived reasons, snooze/coverage, unanswered inbound replies, agreed-later tour suppression, stalled opportunities; `crm/attention` |
| Automation | Versioned rules/configuration, preview, durable queue/retry/dead-letter, lease fencing/recovery, daily digest snapshots; `crm/automation` |
| Communications | Templates, send-time stop checks, safe retries, uncertain outcomes; local sandbox captures, not real customer email; `crm/comms` |
| Reports | Explicit metrics, period/filter/drill-down, exact minor-unit money, atomic spend/audit; `crm/reporting` |
| Company setup | Profile/logo, first-run checklist, configurable vocabulary/cadence/stages/currency/timezone; `crm/core` |
| Operations | Backup verification/restore, optional AES-GCM encrypted backups, Docker HTTPS kit; `deploy/`, `scripts/new_company.sh`, `docs/INSTALL_NEW_COMPANY.md` |
| UI/QA | CrisGen template styling, mobile journey, demo/pilot/admin guides, CI; `templates/`, `static/crm/`, `tests/`, `e2e/` |

Rule-based research candidates C-R2/C-R3/C-R6 have implementations; their presence is not evidence of approval for every proposed AI feature. Check `context/04_requirements/OPEN_DECISIONS.md` and `context/05_research/AI_AUTOMATION_RESEARCH.md`.

## Non-negotiable business and technical invariants
- ADR-001: sender remains responsible until the recipient accepts the handover.
- ADR-002: pool claiming is atomic/exclusive; release requires coordinator acceptance; overdue work never automatically removes ownership.
- One shared internal workspace; do not add per-record role restrictions, public customer portal, multi-tenancy, property inventory or payout accounting.
- Use service functions, `write_transaction`, same-transaction audit and outbox events where required. Enforce optimistic version checks and durable logical/operation keys.
- Never hold SQLite write transactions across transport calls or other slow I/O. Lease ownership and attempt fencing must protect worker outcomes.
- Use `crm.core.clock.now()` and UTC storage; workspace timezone for display. Use `get_policy()` rather than hardcoded cadences.
- Attention is derived from source facts. Views, notes and merely reading notifications do not satisfy human follow-up.
- Customer send retries retain original stop context; missing context fails closed. Opt-out, archive, reply, rule disable and uncertain-delivery controls must remain effective.
- No real email/customer data in tests. Sandbox captures must say not sent. Password-reset infrastructure is not proof of live mail configuration.
- No committed secrets, TOTP seeds, recovery codes, .env files, runtime databases, demo passwords or backup encryption keys. Use Cursor's environment secrets for needed credentials.
- Respect CSP: no inline script/style. Keep vendor files unchanged; use CrisGen classes/tokens and app CSS. No sideways page scroll at 390px.

## Authority, defaults and open decisions
Confirmed user instructions and accepted ADRs govern product scope. Code and tests establish current implementation; old planning documents remain historical where stale. Defaults are engineering choices documented in `docs/IMPLEMENTATION_DEFAULTS.md`, not business sign-off. OQ-002 lifecycle milestone, OQ-008 notification/onboarding policies, OQ-010 providers/data systems, OQ-011 metric definitions, OQ-012 hosting/recovery and OQ-015 AI promotion/privacy need the recorded owner choices. Preserve existing working defaults while doing independent engineering. Do not repeatedly ask about choices already recorded.

## Evidence and known gaps
Previous hardening: 127 tests passed at bd49e60; hosted CI run 43345965197 passed including desktop/390px journeys. Later product-readiness work reported 158 tests and 16 browser checks before integration. Neither is automatically a current-main pass. Fresh preparation baseline at main fda56b3: 195 tests passed in 8.07s; lint, Django and migration checks passed. This is preparation evidence, not a Cursor environment pass. See RUN_LOG.md; Cursor must rerun in its own environment.

Known gaps: no live customer email transport/reply ingestion; no SSO; no measured scale ceiling; assistive-technology and real-team usability review incomplete; deployment kit exists but no actual target server/backup destination is configured here. MySQL remains deferred. Inbound reply matching is chronological per contact, not explicit message-thread identity. Digest resolved means leaving the recipient's queue, which can include reassignment.

## Primary files to consult
- `context/04_requirements/CRM_Requirements_Baseline_v0.1.md`, `CLIENT_ATTENTION_AND_FOLLOWUP_v0.1.md`, `AUTOMATION_CATALOG.md`, `OPEN_DECISIONS.md`.
- `context/06_architecture/` and module-specific contracts; historical designs need comparison with current code.
- `docs/REQUIREMENTS_MATRIX.md`, `SECURITY.md`, `OPERATIONS.md`, `IMPLEMENTATION_DEFAULTS.md`, `KNOWN_LIMITATIONS.md`, `UI_COMPONENTS.md`.
- `docs/PILOT_TEST_SCRIPT.md`, `ADMIN_GUIDE.md`, `DEMO_SCRIPT.md`, `INSTALL_NEW_COMPANY.md`.
- Tests covering the touched area; `.github/workflows/ci.yml` for actual required checks.

## Definition of done
Current acceptance scenarios work end-to-end on fictional data; meaningful regression tests, lint, migration checks, dependency audit and relevant browser journeys pass; failure/conflict/empty/mobile paths are verified; reviewer findings are resolved; docs and state match the code; commits are pushed and linked in a reviewable PR. Actual production acceptance additionally needs target infrastructure, business-policy review and human pilot evidence, which agents cannot fabricate.
