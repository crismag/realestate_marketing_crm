# CRM development context
Updated: 13 November 2026. Stage: requirements review and workflow definition.

## Read in order
1. [Requirements baseline](04_requirements/CRM_Requirements_Baseline_v0.1.md) — preserved v0.1 snapshot.
2. [Workflow proposal](04_requirements/WORKFLOWS_v0.1.md) — proposed rules and observable scenarios.
3. [Decision register](04_requirements/OPEN_DECISIONS.md) — unresolved business policy; never infer approval.
4. [Current model](project-model.yaml) — current repository/session checkpoint.
5. [Claude handoff](CLAUDE_HANDOFF.md) — bounded next assignment.

The baseline contains the detailed confirmed scope and proposed acceptance criteria. ADR-001 is now approved: the sender retains responsibility until the recipient accepts a handover; see the current workflow and decision register, which supersede the baseline's historical open-policy statement. Later documents supplement it; they do not silently approve or replace it. Keep permanent IDs. Record changes, classifications and affected requirements.

## Latest addition
[Shared client pool policy v0.1](04_requirements/SHARED_POOL_POLICY_v0.1.md) proposes exclusive claiming, coordinator-accepted release and overdue alerts without automatic ownership removal. PROP-031 operating rules are now approved under ADR-002; unspecified technical and exception details remain open. ADR-001 remains approved. Review this policy alongside the broader workflow proposal.

## Current boundaries
Internal Sales and Marketing CRM; one company workspace; unrestricted internal functional access; individual and shared client handling; real estate first with reusable generic workflows. Customer portals and multi-company SaaS are deferred. No application code or stack is selected.

## Next step
Review [Lifecycle and screen organization v0.1](04_requirements/LIFECYCLE_AND_SCREENS_v0.1.md), especially the proposed single-contact model and client conversion milestone. Independent competitor and CrisGen inspection can proceed while business questions remain open. Then produce a proposed screen/module design, followed by architecture and bounded implementation tasks.

## Package status
This is an initial context folder, not a complete execution package. Architecture, verified UI catalogs, contracts, per-task bundles, interface checkpoints, development checklist/run log, project-specific skills and execution/verification companions remain pending. Generate them at the relevant design/planning stage using inspected repository evidence.

## Portfolio attention requirement
[Client attention and follow-up coverage](04_requirements/CLIENT_ATTENTION_AND_FOLLOWUP_v0.1.md) captures REQ-026: proactively resurface forgotten clients, including toured clients with no follow-up task. Queue, digest, metrics and detailed rule behavior are proposed under PROP-033; timing and channels remain open.

## Design and execution context — revision 23
Start with [Context index](CONTEXT_INDEX.md) and [Readiness review](09_development/READINESS_REVIEW.md). Added proposed module boundaries, automation catalog, user coverage, data/interface contracts, verification companions, planning checklist and fixed-revision CrisGen source records. No application code or live automation has been created. Remaining policies are not silently approved.
