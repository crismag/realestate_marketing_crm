# Development execution context — 13 November 2026

## Current authority and goal
The user has authorized autonomous implementation and multi-agent work for the Realstate CRM. Continue the existing Django/SQLite implementation rather than scaffold a replacement. Preserve accepted ADR-001/002, shared internal customer visibility, sandbox-only customer messages and configurable business defaults. MySQL remains a later migration. Earlier fixed-time run instructions apply only to that historical run, not this new assignment.

## Observed implementation
The repository contains eight CRM apps, server-rendered CrisGen screens, a durable SQLite worker, intake API, reports, tests and operations commands. Historical evidence reports 94 tests and 15 browser checks; this run must verify those independently. Historical context documents are specifications, not evidence that current code is absent or production ready.

## Approach
Continue the existing implementation with independent audit and regression-led hardening. Rewriting would discard working code and evidence; expanding into portals, inventory or multi-tenant SaaS would violate current boundaries. Prioritize correctness before optional backlog features.

## Work allocation and acceptance
| Stream | Owned files | Required result |
|---|---|---|
| Messaging | crm/comms/services.py; tests/test_comms_retry.py | Retried messages retain original inquiry context; answered/closed/replied inquiries suppress; stale requests do not enqueue or audit false transitions |
| Worker | crm/automation/worker.py; tests/test_worker_fencing.py | Every outcome is fenced by lease owner, running state and attempt; obsolete workers cannot change newer jobs or message state |
| Reporting integrity | crm/contacts/services.py; crm/reporting/services.py; crm/reporting/views.py; tests/test_reporting_integrity.py | Future inquiries and pre-inquiry responses rejected; spend and audit committed or rolled back together |
| Attention and coordination | crm/attention/services.py; tests/test_attention_agreement.py; context and docs | Agreed future contact pauses tour cadence alerts without concealing unanswered inquiries or overdue tasks; current checkpoint and continuation instructions are accurate |

## Execution steps
- [x] Inspect current code, requirements, limits and historical evidence.
- [x] Allocate disjoint streams to three agents.
- [x] Reproduce each defect with a failing regression test.
- [x] Apply minimal fixes and run focused tests.
- [x] Review integrated diff and run pytest, ruff, migration drift and browser smoke where available.
- [x] Record actual evidence, outstanding gaps and runnable continuation instructions.
- [x] Commit changes and prepare a reviewable repository branch/PR if remote writes are available.

## Review focus
Lease expiry during success/failure/defer; stale repeated manual actions; retry context after customer response; historical timestamps vs future input; audit failure rollback. Never report old test evidence as current execution.

## Added required coverage
Inbound reply attention and durable digest snapshots are implemented in this run, with separate regression suites. See current run report for integrated results.

## Remaining stages
1. Correctness hardening and context reconciliation (this run).
2. Required attention/digest coverage added in this run: inbound replies without inquiries and new/continuing/resolved digest accounting. Review against team workflow during pilot.
3. Complete functional browser, accessibility and representative-volume checks; remediate verified defects.
4. Pilot preparation: document default policy choices and verify backup/restore in target environment.
5. Integrations/release depend on actual hosting, sender/provider and credentials. Do not claim live delivery, deployment, MySQL support or owner acceptance without evidence.

## Checkpoint protocol
Update RUN_LOG and a current run report after integration. Keep historical reports intact. Record commit, commands/results and exact remaining work. New sessions read this file, CLAUDE.md, current run report and known limitations before selecting the highest priority unfinished item. Do not launch unattended sessions or manufacture a twelve-hour keepalive promise.

Hosted GitHub CI, including fresh desktop/mobile browser journeys, passed for code commit bd49e60 in run 43345965197. Draft PR #4 is published. See CURRENT_RUN_REPORT.md.
