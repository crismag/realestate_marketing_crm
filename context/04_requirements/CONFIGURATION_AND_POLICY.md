# Business configuration and policy
Revision 24, proposed. Traces REQ-024 and REQ-018–026.
| Setting family | Examples | Validation / effect |
|---|---|---|
| Terminology/stages | Contact labels, lifecycle codes, sales stages | Stable codes behind labels; history retains version |
| Organization | Teams, pools, coordinator and coverage | Missing notification recipient explicit; no access restrictions implied |
| Attention cadence | Eligible activities, due windows, exceptions | Units/timezone explicit; no invented default intervals |
| Notification policy | Channel, grouping, quiet hours, escalation | Separate internal alerts and customer outreach |
| Rule templates | Onboarding, inquiry, after-tour, digest | Draft/preview before enabled execution; stop semantics declared |
| Metrics | Eligibility, currency/date basis, source | Definition/version visible on reports |
| Preferences | Opt-out/channel restrictions, future contact agreement | Recheck before outreach; conflict handling specified |

Recommend effective-at policy versions; do not retroactively alter recorded execution without trace. Changing cadence can recalculate current queues but should not claim historical performance under a new definition unless report explicitly restates it.
Deleting a referenced stage/pool/rule requires replacement/archive plan. Configuration validation errors preserve input. Concurrent edits need version conflict behavior.
Operational secret settings are injected outside versioned documents. OQ-008/011/012 remain open. This document supplies policy structure, not actual business values.
