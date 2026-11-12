# Scoped execution and review prompts
Revision 24.
## Executor prompt
Read the selected TASK-nnn_CONTEXT.md and only its routed context. Reconcile current model/checklist/log and repository state. Report inspected files, behavior, reused utilities/components, actual commands, existing failures, allowed paths and planned change before implementation. If draft task lacks a business rule/path/contract, record the gap and do not silently invent it. Execute only authorized scope, verify relevant positive/negative/replay cases, and persist evidence and state updates.
## Review prompt
Review the scoped diff against the task, accepted ADR-001/002 and applicable contracts. Report concrete findings with file locations, severity, violated requirement, consequence and fix suggestion. Check ownership, stale transitions, forgotten clients without tasks, timing/stop rules, idempotency, metric reconciliation, authentication, missing failure states and unintended scope. Do not ask for general reassurance.
## Result/handoff structure
Task and status; inspected revision/patch; changed files; acceptance outcomes; exact checks/environment/results; limitations; deviations/decisions; affected stale context; recovery point; next eligible item. A task is not complete merely because tests written by its implementer pass.
