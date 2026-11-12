# Autonomous run plan — 2026-11-12

Run id `autonomous-build-2026-11-12`. Fixed window: **2026-11-12T19:08:03Z → 2026-11-13T07:08:03Z** (12 h).
The deadline was fixed at start; resumes and context resets never extend it. Branch
`claude/project-thread-2p04se` from base `96c10c9`.

## Authority used

The product owner (Cris) asked for an autonomous build of the CRM described in `context/`, with SQLite now
and a MySQL path later, security from the foundation, and reversible technical/product decisions made
without asking. Those decisions are recorded as **implementation defaults** in
[`docs/IMPLEMENTATION_DEFAULTS.md`](../../docs/IMPLEMENTATION_DEFAULTS.md); none is a business approval.
TASK-003's dependency on TASK-001 (owner decisions) was bridged by those defaults, as instructed.

Boundaries kept: no public deployment, purchases, production data or real customer messages; sandbox
transport for customer email; no force-push or history rewrite; no changes to other repositories.

## Stages and order

| Stage | Scope | Depends on |
|---|---|---|
| A | Defaults, contracts, run state | — |
| B | Django foundation, SQLite WAL, auth, audit, worker, test tooling | A |
| C | Capture, search, duplicates, inquiries | B |
| D | Responsibility, claims, pools, handovers (ADR-001/002) | C |
| E | Interactions, tours, tasks, next actions | C, D |
| F | Attention queue and coverage | E |
| G | Durable automation, reminders, notifications, digest | F |
| H | Customer email sandbox, templates, stop policies | G |
| I | Reporting with declared metrics | F |
| J | Acceptance, security, recovery, browser journey, CI, handoff | all |

Each slice is "done" only with persistence, business logic, UI and automated evidence, then a commit and
push. State is written to `AUTONOMOUS_RUN_STATE.json` after each slice. The final 60–90 minutes are reserved
for integration, fixes and handoff.

## Continuity

This cloud session cannot supervise, schedule or relaunch another Claude process. If the session ends,
resume manually with [`RESUME_PROMPT.md`](RESUME_PROMPT.md), either in a new Claude Code session on this
branch or locally with `claude --continue` / `claude --resume` (Claude Code 2.1.322 supports both).
