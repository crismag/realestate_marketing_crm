# MOD-001: Customer relationships
Revision 24 — proposed logical module, not selected service or schema.
## Purpose
Contact identity, company/referral/source links and inquiries.
## Responsibilities
Contact identity, company/referral/source links and inquiries; maintain its own data lifecycle and expose validated operations.
## Non-responsibilities
Assignment mutations and delivery execution belong elsewhere.
## Inputs
Capture payload, search filters, normalized source events.
## Outputs
Contact/inquiry result, duplicate candidates, intake history.
## Public interfaces
Capture/search/update candidate operations; concrete contracts pending.
## Data owned
Contact, inquiry and source-link lifecycle. This module is authoritative for writes; other modules request operations.
## Data consumed
Assignment summary, interaction/work summaries; consume validated snapshots/events rather than reaching into another owner's mutation paths.
## Dependencies
MOD-008 identity/configuration references. Framework/storage/provider choices unresolved.
## Main workflows
Find existing identity before creating; save validated contact and linked inquiry; reuse on repeat interest.
## Business rules
No mandatory customer login; no source/introducer overwrite on assignment.
## Validation rules
Validate references, typed inputs, operation identity and applicable expected versions before persistence. Distinguish missing, invalid and unknown values. Do not invent mandatory fields or timing.
## Error conditions
Invalid input, duplicate candidate, unavailable persistence; never report false success. Record safe correlation context and caller action; retry only documented retryable paths.
## Security considerations
Authenticated internal operations; server-side integrity checks; minimal logged customer data. Shared access does not allow impersonation or external CRM disclosure.
## Observability
Operation/event IDs, outcome, policy/schema version and timestamps; redact secrets. Empty result differs from unavailable data.
## Configuration
Only versioned settings applicable to this capability; OQ-008/012 constraints remain explicit.
## Test strategy
Use isolated synthetic fixtures. Verify happy path, invalid references, concurrency where applicable, replay and unavailable dependency. UI loading/empty/error/conflict checks where this module has a screen. No tests executed by this document.
## Open questions
Minimum identity, duplicate matching, company relations and migration sources.
## Related requirements
REQ-003, REQ-004, REQ-005, REQ-006, REQ-024, FR-001.
## Related architectural decisions
ADR-001/002 apply where responsibility is consumed; do not reinterpret accepted policies. Proposed module arrangement is PROP-034; detailed implementation remains pending review.
