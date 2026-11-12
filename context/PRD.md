# Product requirements overview
Revision 24 — review draft. This file is a projection, not another editable requirements authority.
Purpose: an internal Sales and Marketing CRM that prevents forgotten relationships, coordinates shared clients and automates follow-up. Real estate is the first configuration; generic sales concepts remain reusable.
Users: [target users](01_discovery/TARGET_USERS.md). All five internal groups share functional access within one company workspace. Anonymous users cannot read internal records. Customer portal is deferred.
Requirements authority: [baseline](04_requirements/CRM_Requirements_Baseline_v0.1.md), [current decisions](04_requirements/OPEN_DECISIONS.md), [attention extension](04_requirements/CLIENT_ATTENTION_AND_FOLLOWUP_v0.1.md) and project-model.yaml.
Core journeys: capture → assign/claim → interact → plan next action → surface attention → coordinate handover → record outcomes. An agent must see forgotten clients even if no task was ever created.
Approved policies: sender accountable until accepted handover; atomic exclusive claims; coordinator-accepted pool release; overdue work alerts without automatic ownership removal.
Proposed MVP: capture/search/history, pools and handovers, task/interaction logging, attention lists and bounded notifications; basic source/workload metrics. Campaign earnings analytics depends on data definitions and integrations.
Excluded initially: customer portal, multi-company SaaS, role restrictions, property inventory, booking-slot priority, accounting/commission payouts, autonomous AI prospecting.
Success is measured using response/follow-up coverage, overdue work and outcome metrics once eligibility/targets are agreed. No numeric target or delivery date adopted.
See [roadmap](07_tasks/ROADMAP.md), [acceptance catalog](10_validation/ACCEPTANCE_CATALOG.md) and [readiness](09_development/READINESS_REVIEW.md).
