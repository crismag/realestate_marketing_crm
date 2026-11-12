# TASK-009: Add configured onboarding and customer follow-up
Revision 24. Status: draft. Not implementation-ready: resolve listed policies and exact application file paths first.
## Business purpose and objective
Implement explicitly enabled provider adapter and approved templates/stop policy in sandbox first.
## Relevant requirements and design
REQ-018, REQ-020, REQ-023. Design: MOD-005, MOD-006. Source model and related module file(s) are authoritative; proposed defaults remain proposed.
## Dependencies and entry conditions
TASK-008. Load current model/checklist/run log and confirm dependency evidence before selecting work.
## Required context
Load only relevant rows from ../04_requirements/USER_MODULE_MATRIX.md and ../01_discovery/TARGET_USERS.md; affected modules in ../06_architecture/modules/; applicable contracts/checkpoints in ../08_interfaces/; relevant acceptance rows in ../10_validation/ACCEPTANCE_CATALOG.md. For UI load scoped CrisGen records. Every implementation slice also loads runtime, environment, security, verification and recovery companions in ../09_development/.
Project playbooks: SKL-002, SKL-003; see ../12_agent_skills/SKILL_INDEX.md.
## Discovery and contracts
Verified provider contract and isolated sandbox credentials. Before code, inspect full affected files, actual schema/type/runtime validation and manifest commands; record existing failures. No invented endpoint, selector, app path or test script.
## Allowed file scope
Selected email adapter, templates/preferences, related automation/tests; exact paths unresolved. Shared updates limited to model, traceability, checklist and run-log entries affected by this task. Draft application scopes require exact path confirmation before readiness.
## Prohibited changes
No customer portal, tenancy, restrictive internal roles, commission payouts, property inventory, unrelated refactors, upstream generated CrisGen edits, production sends/deployment or destructive data resets. Do not treat this context-generation request as application implementation approval.
## Acceptance criteria
AT-004: correct onboarding event/recipient; reply/opt-out/quiet-hours checked; no blind resend on uncertain result; preview sends nothing.
## Tests and evidence
Contract plus separate real sandbox delivery; replay/signature cases where callbacks used; no production messages in tests.
All application checks begin not_run. Record environment, fixture, command/source, commit and working-tree identity, result and artifacts. No mock pass proves live delivery.
## Interface/checklist routing
Use affected INT/HOK/ICP rows where defined. TASK-005 → ICP-001/002; TASK-007 → ICP-003/005; TASK-008/009 → ICP-004; TASK-010 → ICP-005. Other operations need scoped contracts before implementation.
Each task maps to CHK-013 in the development checklist. Preserve original CHK-001–004 planning entries.
## Open issues
OQ-008/010 sender/provider/template/stop policy. Ask only what blocks this slice; continue independent authorized documentation where possible.
## Definition of completion and handoff
Acceptance evidence plus scoped diff review, updated model/checklist/log and no prohibited changes. Unavailable checks are blocked/not_run, never passed. Persist decisions/deviations and next eligible action. Later changes invalidate affected evidence.
