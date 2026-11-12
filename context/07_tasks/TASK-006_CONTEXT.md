# TASK-006: Record interactions and next actions
Revision 24. Status: draft. Not implementation-ready: resolve listed policies and exact application file paths first.
## Business purpose and objective
Implement typed tour/contact evidence and linked task scheduling so attention has trustworthy facts.
## Relevant requirements and design
REQ-015, REQ-016, REQ-020, REQ-026. Design: MOD-002, MOD-003. Source model and related module file(s) are authoritative; proposed defaults remain proposed.
## Dependencies and entry conditions
TASK-004, TASK-005. Load current model/checklist/run log and confirm dependency evidence before selecting work.
## Required context
Load only relevant rows from ../04_requirements/USER_MODULE_MATRIX.md and ../01_discovery/TARGET_USERS.md; affected modules in ../06_architecture/modules/; applicable contracts/checkpoints in ../08_interfaces/; relevant acceptance rows in ../10_validation/ACCEPTANCE_CATALOG.md. For UI load scoped CrisGen records. Every implementation slice also loads runtime, environment, security, verification and recovery companions in ../09_development/.
Project playbooks: SKL-001, SKL-002, SKL-003; see ../12_agent_skills/SKILL_INDEX.md.
## Discovery and contracts
Interaction and task validation contracts. Before code, inspect full affected files, actual schema/type/runtime validation and manifest commands; record existing failures. No invented endpoint, selector, app path or test script.
## Allowed file scope
Interaction/task operations and affected profile UI/tests; exact paths unresolved. Shared updates limited to model, traceability, checklist and run-log entries affected by this task. Draft application scopes require exact path confirmation before readiness.
## Prohibited changes
No customer portal, tenancy, restrictive internal roles, commission payouts, property inventory, unrelated refactors, upstream generated CrisGen edits, production sends/deployment or destructive data resets. Do not treat this context-generation request as application implementation approval.
## Acceptance criteria
Separate attempt/reply/conversation/tour/view; occurrence and recording time preserved; task assignee distinct from client owner.
## Tests and evidence
Invalid/backdated policy cases as agreed; source replay; completed task does not transfer client.
All application checks begin not_run. Record environment, fixture, command/source, commit and working-tree identity, result and artifacts. No mock pass proves live delivery.
## Interface/checklist routing
Use affected INT/HOK/ICP rows where defined. TASK-005 → ICP-001/002; TASK-007 → ICP-003/005; TASK-008/009 → ICP-004; TASK-010 → ICP-005. Other operations need scoped contracts before implementation.
Each task maps to CHK-010 in the development checklist. Preserve original CHK-001–004 planning entries.
## Open issues
Eligible activity/reset rules and timezones. Ask only what blocks this slice; continue independent authorized documentation where possible.
## Definition of completion and handoff
Acceptance evidence plus scoped diff review, updated model/checklist/log and no prohibited changes. Unavailable checks are blocked/not_run, never passed. Persist decisions/deviations and next eligible action. Later changes invalidate affected evidence.
