# Open decisions
Updated: 13 November 2026. Owner: product owner unless technical discovery is indicated.
These are unresolved, not blockers on unrelated documentation or research.

| ID | Question | Proposed default | Impacts |
|---|---|---|---|
| OQ-002 | Approve one-contact lifecycle model, and what milestone creates a client? | PROP-032: lead = unqualified; prospect = qualified; client = accepted transaction milestone; see LIFECYCLE_AND_SCREENS_v0.1.md | Capture, reporting, sales process |
| OQ-008 | What event is onboarding; who receives emails; what timing/channels/stop policies apply? | Explicit configurable event and bounded enabled rules | REQ-018–023 |
| OQ-010 | Which systems supply intake, email and engagement data? | Select only verified integrations | REQ-003–006, REQ-018–023 |
| OQ-011 | What do spending, earnings, signup and engagement mean? | Named formulas with reconciled source data | REQ-022 |
| OQ-012 | Hosting, scale, authentication, recovery, retention, currency and timezone constraints? | Unknown; do not select stack prematurely | Architecture |
| OQ-013 | Are special groups beyond the five named groups required? | Existing groups only until clarified | User/module context |
| OQ-014 | Is support full case management or client follow-up coordination? | Keep support linked to customer history; no full helpdesk assumed | Engagement scope |
| OQ-015 | Which AI/automation candidates (if any) to promote, and may contact data be sent to an external AI provider? | Proposal: promote rule-based C-R2, C-R3, C-R6 first; pilot AI only as read-only C-A1 on demo data behind an off-by-default switch; see ../05_research/AI_AUTOMATION_RESEARCH.md | REQ-015–017, REQ-020, REQ-022, REQ-026; PRD first-release scope |

Resolved 13 November 2026: OQ-006 — user approved sender accountability until recipient acceptance (ADR-001). Impacts REQ-015, REQ-019 and REQ-020; workflow and model updated. Baseline v0.1 remains an unchanged historical snapshot; this decision supersedes its statement that the policy is unapproved. No implementation exists to invalidate.

Previously resolved: OQ-001 initial business boundary, OQ-004 customer profile boundary, OQ-005 meaning of usage priority, OQ-007 business rather than church scope. OQ-003 public access is deferred.

Important distinction: unrestricted internal function access is agreed. Authentication remains necessary; public website intake does not imply public CRM access. Do not introduce role restrictions under the guise of supervisory views.

Record each answer with date, source, affected requirements and invalidated downstream artifacts. No proposed default is approved until the owner adopts it.

Resolved 13 November 2026: OQ-009 — ADR-002 approves exclusive claiming, coordinator-accepted release and overdue alerts without automatic ownership removal. Unspecified priority, timing and emergency override policies remain open. No implementation exists to invalidate.
