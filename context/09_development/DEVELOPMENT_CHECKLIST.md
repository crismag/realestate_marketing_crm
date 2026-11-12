# Development checklist — model 24/revision 2
Projection of DEVELOPMENT_CHECKLIST.yaml; machine source and model govern updates.

Planning items CHK-001–004 remain under review/in progress. Generated task briefs and draft skills are not completed software.

| Checklist | Task | Status | Dependencies |
|---|---|---|---|
| CHK-005 | [TASK-001: Resolve workflow and delivery constraints](../07_tasks/TASK-001_CONTEXT.md) | ready (documentation/research only) | none |
| CHK-006 | [TASK-002: Complete relevant reference and CrisGen inspection](../07_tasks/TASK-002_CONTEXT.md) | ready (documentation/research only) | none |
| CHK-007 | [TASK-003: Establish contracts and isolated project foundation](../07_tasks/TASK-003_CONTEXT.md) | implemented; local evidence (owner review of OQ-012 pending) | TASK-001 |
| CHK-008 | [TASK-004: Capture and search one customer identity](../07_tasks/TASK-004_CONTEXT.md) | implemented; local evidence | TASK-003 |
| CHK-009 | [TASK-005: Claim shared clients and accept handovers](../07_tasks/TASK-005_CONTEXT.md) | implemented; local evidence (AT-001/002 passed) | TASK-004 |
| CHK-010 | [TASK-006: Record interactions and next actions](../07_tasks/TASK-006_CONTEXT.md) | implemented; local evidence | TASK-004, TASK-005 |
| CHK-011 | [TASK-007: Surface forgotten clients and attention coverage](../07_tasks/TASK-007_CONTEXT.md) | implemented; local evidence (AT-003/005 passed) | TASK-006 |
| CHK-012 | [TASK-008: Execute bounded internal reminders and digest](../07_tasks/TASK-008_CONTEXT.md) | implemented; local evidence (AT-004/009/011 passed) | TASK-007 |
| CHK-013 | [TASK-009: Add configured onboarding and customer follow-up](../07_tasks/TASK-009_CONTEXT.md) | implemented with sandbox transport only; real provider not_run | TASK-008 |
| CHK-014 | [TASK-010: Report workload and sourced sales/marketing outcomes](../07_tasks/TASK-010_CONTEXT.md) | implemented; local evidence; earnings unavailable (OQ-011) | TASK-007 |
| CHK-015 | [TASK-011: Enforce agreed automated checks in CI](../07_tasks/TASK-011_CONTEXT.md) | implemented; hosted CI passed (head 0224dab) | TASK-003 |
| CHK-016 | [TASK-012: Verify release candidate and pilot handoff](../07_tasks/TASK-012_CONTEXT.md) | in progress; local acceptance evidence done, pilot not started | TASK-005, TASK-007, TASK-008, TASK-010, TASK-011 |

Autonomous build run 2026-11-12/13 implemented TASK-003 to TASK-011 locally; evidence and gaps are in [docs/REQUIREMENTS_MATRIX.md](../../docs/REQUIREMENTS_MATRIX.md). "Implemented" means built and verified by automated tests in the build environment, not accepted by the product owner. Implementation defaults remain unapproved (see [docs/IMPLEMENTATION_DEFAULTS.md](../../docs/IMPLEMENTATION_DEFAULTS.md)). TASK-001 and TASK-002 (owner decisions and reference research) are still open.
