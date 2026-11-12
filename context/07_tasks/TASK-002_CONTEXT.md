# TASK-002: Complete relevant reference and CrisGen inspection
Revision 24. Status: ready. Documentation/research scope only; no application scaffold authorized.
## Business purpose and objective
Inspect reference patterns and actual UI target APIs when selected; map only observed behavior to required screens.
## Relevant requirements and design
REQ-002, REQ-025. Design: MOD-001, MOD-002, MOD-004. Source model and related module file(s) are authoritative; proposed defaults remain proposed.
## Dependencies and entry conditions
None for the bounded documentation/research portion. Load current model/checklist/run log and confirm dependency evidence before selecting work.
## Required context
Load only relevant rows from ../04_requirements/USER_MODULE_MATRIX.md and ../01_discovery/TARGET_USERS.md; affected modules in ../06_architecture/modules/; applicable contracts/checkpoints in ../08_interfaces/; relevant acceptance rows in ../10_validation/ACCEPTANCE_CATALOG.md. For UI load scoped CrisGen records. Every implementation slice also loads runtime, environment, security, verification and recovery companions in ../09_development/.
Project playbooks: SKL-001, SKL-003; see ../12_agent_skills/SKILL_INDEX.md.
## Discovery and contracts
none; read-only research plus context edits. Before code, inspect full affected files, actual schema/type/runtime validation and manifest commands; record existing failures. No invented endpoint, selector, app path or test script.
## Allowed file scope
context/05_research/; context/06_architecture/design_system/; matrix and model/checklist/log. Shared updates limited to model, traceability, checklist and run-log entries affected by this task. Draft application scopes require exact path confirmation before readiness.
## Prohibited changes
No customer portal, tenancy, restrictive internal roles, commission payouts, property inventory, unrelated refactors, upstream generated CrisGen edits, production sends/deployment or destructive data resets. Do not treat this context-generation request as application implementation approval.
## Acceptance criteria
Source URL/path/date/revision retained; docs versus runtime distinguished; no invented API/import; reference-only research can proceed while target selection is unresolved.
## Tests and evidence
Check source-qualified symbols, framework compatibility, relative links and missing evidence.
All application checks begin not_run. Record environment, fixture, command/source, commit and working-tree identity, result and artifacts. No mock pass proves live delivery.
## Interface/checklist routing
Use affected INT/HOK/ICP rows where defined. TASK-005 → ICP-001/002; TASK-007 → ICP-003/005; TASK-008/009 → ICP-004; TASK-010 → ICP-005. Other operations need scoped contracts before implementation.
Each task maps to CHK-006 in the development checklist. Preserve original CHK-001–004 planning entries.
## Open issues
Selected framework still open; public reference review is independent. Ask only what blocks this slice; continue independent authorized documentation where possible.
## Definition of completion and handoff
Acceptance evidence plus scoped diff review, updated model/checklist/log and no prohibited changes. Unavailable checks are blocked/not_run, never passed. Persist decisions/deviations and next eligible action. Later changes invalidate affected evidence.
