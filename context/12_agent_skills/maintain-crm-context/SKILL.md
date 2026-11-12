---
name: maintain-crm-context
description: Use when selecting CRM tasks, recording decisions, updating context or handing off a scoped agent session; excludes application work without a ready authorized task.
---
# SKL-003: maintain-crm-context
Status: draft export, model 24. Not installed into any personal/agent runtime. Not behavior-tested.
## When to use / exclusions
Use when selecting CRM tasks, recording decisions, updating context or handing off a scoped agent session; excludes application work without a ready authorized task.
## Required context and revision
Read [source context](../../project-model.yaml) and [related context](../../07_tasks/ROADMAP.md), [model](../../project-model.yaml), selected task, [checklist](../../09_development/DEVELOPMENT_CHECKLIST.yaml) and [run log](../../09_development/RUN_LOG.md). Reconcile revision before use; mixed artifact revisions require scoped impact review.
## Preconditions and scope
Use only the selected task's allowed files. Application paths/commands not yet verified mean dependent implementation is blocked. Read-only source inspection and scoped context edits may proceed. No secrets, production sends, deployment, role restrictions or upstream generated-target edits.
## Procedure
Load current model/checklist/log and selected task. Distinguish user-approved rules from proposals; preserve IDs and historical baseline. Reconcile repo revision and dependent scope. Update model first, assess downstream artifacts/evidence, then regenerate only affected projections and append run evidence. Record unresolved blockers and select independent eligible documentation work where available.
## Required output
Scoped finding/change record; inspected sources/revision; acceptance/check outcomes; unresolved gaps; affected stale records. Update model/checklist/run log after each atomic step and before advancing. Preserve unrelated changes and historical evidence.
## Verification
Check links/structured companions, task scope/dependencies, source provenance and acceptance evidence. A pending or failed check cannot become done. Confirm durable write before claiming handoff saved.
## Failure and recovery
Report concrete blocker and affected task. Preserve working changes; use scoped recovery guidance. Never invent a passing test, API or completion. Handoff current task, revision, files, evidence and next eligible action.
## Traceability and maintenance
All modules, all context tasks, ADR-001/002.
Any requirement/design/contract change triggers impact review and stale marking. Owner: project context maintainer.
