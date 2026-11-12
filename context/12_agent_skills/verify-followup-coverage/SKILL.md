---
name: verify-followup-coverage
description: Use when designing or verifying CRM attention, follow-up clocks, reminder routing or coverage metrics; excludes production customer outreach authorization.
---
# SKL-002: verify-followup-coverage
Status: draft export, model 24. Not installed into any personal/agent runtime. Not behavior-tested.
## When to use / exclusions
Use when designing or verifying CRM attention, follow-up clocks, reminder routing or coverage metrics; excludes production customer outreach authorization.
## Required context and revision
Read [source context](../../04_requirements/CLIENT_ATTENTION_AND_FOLLOWUP_v0.1.md) and [related context](../../04_requirements/METRIC_DICTIONARY.md), [model](../../project-model.yaml), selected task, [checklist](../../09_development/DEVELOPMENT_CHECKLIST.yaml) and [run log](../../09_development/RUN_LOG.md). Reconcile revision before use; mixed artifact revisions require scoped impact review.
## Preconditions and scope
Use only the selected task's allowed files. Application paths/commands not yet verified mean dependent implementation is blocked. Read-only source inspection and scoped context edits may proceed. No secrets, production sends, deployment, role restrictions or upstream generated-target edits.
## Procedure
Identify affected attention reason, clock, eligibility and task/relationship routing. Use fixed-clock synthetic clients including tour with no task, profile view, reply, opt-out, overlapping reasons and pending transfer. Inspect actual facts/policy before evaluating. Test restart/replay/current-state recheck; reconcile unique counts and drill-down. Keep human attempt, conversation and delivery distinct.
## Required output
Scoped finding/change record; inspected sources/revision; acceptance/check outcomes; unresolved gaps; affected stale records. Update model/checklist/run log after each atomic step and before advancing. Preserve unrelated changes and historical evidence.
## Verification
Verify AT-003/004/005/011 and relevant ICP-003/004/005; record missing/unknown facts separately from zero, mock versus real integration and current-owner versus task-assignee routing.
## Failure and recovery
Report concrete blocker and affected task. Preserve working changes; use scoped recovery guidance. Never invent a passing test, API or completion. Handoff current task, revision, files, evidence and next eligible action.
## Traceability and maintenance
MOD-003–007, REQ-016–023, REQ-026; TASK-006–010/012.
Changes to cadence, activity meanings, recipient policy or metric formulas invalidate affected evidence. Owner: sales operations/product owner.
