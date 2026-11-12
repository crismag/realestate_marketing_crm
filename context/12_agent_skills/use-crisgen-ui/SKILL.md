---
name: use-crisgen-ui
description: Use when designing or implementing CRM UI with the designated CrisGen source; excludes generic backend work and upstream library edits.
---
# SKL-001: use-crisgen-ui
Status: draft export, model 24. Not installed into any personal/agent runtime. Not behavior-tested.
## When to use / exclusions
Use when designing or implementing CRM UI with the designated CrisGen source; excludes generic backend work and upstream library edits.
## Required context and revision
Read [source context](../../06_architecture/design_system/DESIGN_SOURCE.yaml) and [related context](../../06_architecture/design_system/UI_REUSE_MAP.md), [model](../../project-model.yaml), selected task, [checklist](../../09_development/DEVELOPMENT_CHECKLIST.yaml) and [run log](../../09_development/RUN_LOG.md). Reconcile revision before use; mixed artifact revisions require scoped impact review.
## Preconditions and scope
Use only the selected task's allowed files. Application paths/commands not yet verified mean dependent implementation is blocked. Read-only source inspection and scoped context edits may proceed. No secrets, production sends, deployment, role restrictions or upstream generated-target edits.
## Procedure
Resolve fixed source commit and current app target; inspect selected canonical spec, actual target API/types/examples and theme setup. Choose verified public patterns/components before bespoke equivalents. Map only affected user/section rows and bindings. Record source/compatibility gaps rather than invent imports. Compose CRM behavior in allowed app files after task scope is ready.
## Required output
Scoped finding/change record; inspected sources/revision; acceptance/check outcomes; unresolved gaps; affected stale records. Update model/checklist/run log after each atomic step and before advancing. Preserve unrelated changes and historical evidence.
## Verification
Inspect exact public exports, props/events, focus/keyboard and loading/empty/error/conflict states; verify consuming app behavior at chosen viewports. Library docs/tests are not app integration evidence.
## Failure and recovery
Report concrete blocker and affected task. Preserve working changes; use scoped recovery guidance. Never invent a passing test, API or completion. Handoff current task, revision, files, evidence and next eligible action.
## Traceability and maintenance
MOD-001–008, REQ-002, REQ-024, REQ-025; UI tasks TASK-002/004–010/012.
Source target/spec/export/theme changes invalidate affected mappings and UI checkpoints. Owner: project designer.
