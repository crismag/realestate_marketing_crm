# Open decisions
Updated: 13 November 2026. Owner: product owner unless technical discovery is indicated.
These are unresolved, not blockers on unrelated documentation or research.

| ID | Question | Proposed default | Impacts |
|---|---|---|---|
| OQ-006 | Who is accountable during pending handover? | Sender until explicit acceptance | REQ-015, REQ-019, REQ-020 |
| OQ-002 | What differentiates lead, prospect and client? | One contact identity with separate lifecycle and opportunities | Capture, reporting, sales process |
| OQ-008 | What event is onboarding; who receives emails; what timing/channels/stop policies apply? | Explicit configurable event and bounded enabled rules | REQ-018–023 |
| OQ-009 | Can pool records be claimed and when released? | Atomic exclusive claim; no automatic release without policy | REQ-014 |
| OQ-010 | Which systems supply intake, email and engagement data? | Select only verified integrations | REQ-003–006, REQ-018–023 |
| OQ-011 | What do spending, earnings, signup and engagement mean? | Named formulas with reconciled source data | REQ-022 |
| OQ-012 | Hosting, scale, authentication, recovery, retention, currency and timezone constraints? | Unknown; do not select stack prematurely | Architecture |
| OQ-013 | Are special groups beyond the five named groups required? | Existing groups only until clarified | User/module context |
| OQ-014 | Is support full case management or client follow-up coordination? | Keep support linked to customer history; no full helpdesk assumed | Engagement scope |

Previously resolved: OQ-001 initial business boundary, OQ-004 customer profile boundary, OQ-005 meaning of usage priority, OQ-007 business rather than church scope. OQ-003 public access is deferred.

Important distinction: unrestricted internal function access is agreed. Authentication remains necessary; public website intake does not imply public CRM access. Do not introduce role restrictions under the guise of supervisory views.

Record each answer with date, source, affected requirements and invalidated downstream artifacts. No proposed default is approved until the owner adopts it.
