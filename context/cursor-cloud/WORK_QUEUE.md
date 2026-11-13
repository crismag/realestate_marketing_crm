# Autonomous development queue

This queue continues an existing implementation. Reconcile every task with current source, latest main and open PRs before work. Skip implemented behavior only after verification, not because a historical report says done. Implementation defaults remain editable engineering decisions. Use current acceptance catalog/requirement IDs; new optional features need clearly labeled derived acceptance criteria rather than invented approved requirements.

## Priorities and dependency order
| ID | Priority / dependency | Deliverable | Completion evidence |
|---|---|---|---|
| CC-000 | P0, first | Reconcile remote source and requirements; establish merged baseline | Actual SHA, current inventory, all baseline results and failures |
| CC-010 | P0, after 000 | Integrated security/data/workflow hardening | Reproductions, fixes, reviewer findings and regressions |
| CC-020 | P1, parallel with 010 on disjoint files | Full cloud UI and accessibility verification | Desktop/mobile evidence; automated checks; human-test gaps stated |
| CC-030 | P1, after stable 010 | Representative scale and worker recovery measurements | Reproducible measurements, query counts, fault recovery and limits |
| CC-040 | P1, after 010 | Disposable upgrade/backup/restore/deployment drill | Fresh+upgrade migration and encrypted restore evidence; runbook corrections |
| CC-050 | P2, after 010/020 | Pipeline board using existing opportunities | Current functionality reconciled; source-backed board/filter tests |
| CC-060 | P2, after 050 or independently | Saved dynamic contact filters | Owner-scoped filter configuration without record visibility restrictions |
| CC-070 | P2, after 050 | Tour/viewing calendar over existing tasks | No parallel source of truth; time/collision/mobile evidence |
| CC-080 | P3, after core gates | Integration readiness and operator review package | Provider contract/tests/runbooks; exact external inputs still required |
| CC-090 | Final, after ready tasks | Integrated release candidate and durable handoff | Current-source checks, PR/artifacts, gap matrix, precise next actions |

CC-050/060/070 are proposed enhancements drawn from the existing backlog, not claims of previously accepted requirement detail. The user authorizes autonomous reversible development; document the minimal design/defaults before implementation, keep existing flows and don't introduce excluded scope. If a proposed feature is no longer wanted according to a newer instruction, defer it and continue other work.

## CC-000 — repository reconciliation and baseline
Read root AGENTS/CLAUDE, current handoff/state, requirements matrix, latest run log, known limits and open PRs. Inspect the current selected branch against main. Never reset to the snapshot commit or replay already merged PRs. Update PROJECT_CONTEXT only where code evidence shows changes.

Create a requirement coverage matrix with implemented / partial / missing / not verified / deferred. Separate business decisions from engineering blockers. Run environment setup, pytest, Ruff, Django check, migration drift, dependency audit and browser journey. Record command, environment, SHA, exit status, counts and artifact paths. Baseline failures become explicit P0 tasks; do not relabel them passed.

Files: `context/cursor-cloud/{RUN_STATE.json,RUN_LOG.md,PROJECT_CONTEXT.md,WORK_QUEUE.md}`, `docs/REQUIREMENTS_MATRIX.md`. Product code only under separately scoped fix tasks.

## CC-010 — integrated correctness/security audit
Split independent audit domains after inspection:
- Accounts: password change/reset, login throttle/lockout, TOTP setup/verification/recovery, inactive users, session state and no bypass during forced password change.
- Contacts/import/merge: validation and atomicity, cancellation/replay, relationship reassignment, normalized matching, merge preservation of inquiries/interactions/tasks/watches/audit and idempotency conflicts.
- Responsibility: claim/accept/release races, departed colleagues, sender accountability and no automatic ownership loss.
- Worker/comms: lease fencing across attempts, stop context, quiet hours, opt-out, uncertain transport, retry/cancel races, digest comparison and routing gaps.
- Reporting: chronology, source counts/drill-down reconciliation, exact money, zero/unknown distinctions and spend/audit rollback.

Owned sources are the corresponding `crm/<app>/` service files plus new regression files; allocate exact paths per worker before editing. Start with reproduction tests that fail for the actual defect. Preserve historical data semantics; label migration/backfill decisions. Run focused tests then the full suite; negative authorization, conflict and repeated-delivery cases must remain green. Independent reviewer must examine integrated outcomes.

## CC-020 — cloud UX and accessibility
Use `docs/PILOT_TEST_SCRIPT.md`, `DEMO_SCRIPT.md`, templates and `e2e/journey.cjs`. Walk capture→tour→suggested follow-up→attention→pool claim→handover acceptance→reports as agent, coordinator and administrator. Include CSV preview/cancel/import, duplicate merge, departed staff and company setup. Test keyboard navigation, labels/errors, focus, contrast, empty/filter-empty, invalid form data retention, confirmations and 390px overflow.

Use one owner for `templates/`, `static/crm/crm.css` and browser tests. Do not edit vendor CSS or weaken CSP. Automated accessibility checks may be added as dev-only tools with lockfile changes and reproducible invocation; they are not a screen-reader audit. Capture exact pages/viewports/screenshots and correct verified defects. Keep user usability/sign-off explicitly not run unless actual people participate.

## CC-030 — performance and reliability
Create a reproducible opt-in benchmark/fault scenario under `scripts/` with fictional, isolated datasets. Measure representative 1k/5k/10k contacts and supporting interactions/tasks, attention/digest/report queries, worker backlog and write contention. First record hardware/runtime and baseline p50/p95, query counts and DB size; compare relative regressions on the same environment. Avoid arbitrary unit-test latency thresholds and unbounded data generation.

Exercise interrupted worker/expired lease, duplicate events, scheduler catch-up and DB busy responses. Optimize verified bottlenecks within `crm/attention`, `automation` and reporting without changing outputs. Keep normal tests fast; volume runs opt-in. Record tested capacity and limits instead of declaring internet-scale readiness. Multiple cloud agents must never share the benchmark DB.

## CC-040 — operations drill
Inspect `deploy/`, `Dockerfile`, `scripts/new_company.sh`, backup/restore commands and install guide. In disposable cloud resources, verify fresh installation and upgrade from a prior populated fixture, encrypted backup generation, wrong-key rejection, backup manifest verification, restore to a separate DB, row/source reconciliation and web/worker restart. Prove migrations preserve contact/assignment/history and new digest baselines.

Use temporary random credentials and keys; clean test services, ports and data afterward. If Docker is unavailable, run Python-level checks, record the Docker-specific blocker and continue. Never overwrite a production DB, provision a billable server, configure public DNS/TLS or claim deployment acceptance. Update runbook with measured restore steps and remaining site-specific choices.

## CC-050 — opportunity pipeline board
Minimal design: another view of existing `Opportunity` records and configured stages, with filters and links to the same contact/opportunity details. Stage changes use existing service/version/audit semantics; no new property inventory or second pipeline datastore. Prefer server-rendered controls with accessible keyboard forms over a mandatory drag-and-drop layer.

Inspect `crm/contacts/models.py`, service/view/URL/form paths, existing opportunity templates and app CSS. Add only the needed route/template/service extension plus new workflow tests. Acceptance: stage totals match underlying records/filters, stale version conflicts retain current data, closed deals follow existing rules, 390px layout is usable and source history remains accurate. Add drag/drop only if accessible and justified by the recorded design.

## CC-060 — saved dynamic filters
Minimal design: save a user's contact search/filter/sort configuration, not a cached membership list and not a record-access restriction. Reuse `search_contacts` validated inputs; allow create/rename/delete/apply and clearly indicate active filters. Watch semantics and ownership remain separate.

Inspect contacts query/forms/views and Watch models first; choose an explicit small schema and migration via coordinator. Test filters reevaluate when contact data/assignment changes, invalid serialized fields are rejected, one user cannot edit another's saved configuration and everyone retains shared customer visibility. Existing watch/unwatch behavior must remain unchanged. Measure large-list queries with CC-030 tooling if affected.

## CC-070 — task-backed tour calendar
Minimal design: a day/week/list view of scheduled tour/viewing tasks using existing task records and workspace timezone. Do not infer a completed tour merely from a planned task or store separate duplicate calendar events. Preserve assignee/responsibility differences; log actual interactions through existing services.

Inspect task kinds/schema and UI; document the minimal start/duration fields only if the current model cannot represent scheduling. Coordinator owns migration order. Test UTC/local-day boundaries, date-range filters, cancelled/completed tasks, overdue tasks, assignee changes, mobile/keyboard navigation and daylight-saving transitions where relevant. An overlap warning must not silently change ownership or block all legitimate simultaneous tasks. No external calendar provider is assumed.

## CC-080 — integration readiness
Reconcile remaining product/provider needs with OQ-008/010/015 and existing mail configuration. Prepare a provider-neutral contract and sandbox test coverage for selected requirements. Document sender verification, callbacks/signature verification, bounce/opt-out handling, idempotency and secrets required before activation. Keep staff/customer email and password-reset mail semantics distinct.

Do not choose a paid provider, send messages or put customer data into AI services without the recorded decision and credentials. If those are absent, finish adapter contract/runbook/demo readiness and mark actual integration blocked with the exact missing inputs. Do not endlessly scaffold unused providers or add SSO/AI because it is on a generic wish list.

## CC-090 — whole-branch release candidate
Run all required checks and independent review on the integrated code. Reconcile tests and evidence with requirements; ensure no stale "not implemented" claims for completed features. Update admin/demo/pilot/install docs for actual changes. Provide a PR with problem/result, migrations, compatibility, exact check results, screenshots, known limits and pilot dependencies. Record branch/commit/PR/check-run IDs in state.

If all engineering tasks are complete and remaining work needs real accounts, target infrastructure or human feedback, checkpoint and report completion of the scoped development queue plus those dependencies. Do not invent more features merely to stay active and do not claim to be continuously running after the cloud run ends.
