# MOD-007: Sales and measurement
Revision 24 — proposed logical module, not selected service or schema.
## Purpose
Proposed opportunities/campaign/spend inputs and reconciled metric views.
## Responsibilities
Proposed opportunities/campaign/spend inputs and reconciled metric views; maintain its own data lifecycle and expose validated operations.
## Non-responsibilities
Does not overwrite domain facts to improve statistics.
## Inputs
Declared source records, eligibility/formula version, filters/currency/period.
## Outputs
Outcome records and report drill-down with missing-data/freshness.
## Public interfaces
Read/report and outcome operation candidates; ICP-005.
## Data owned
Opportunity/campaign/spend records if adopted; measurement definitions/projections. This module is authoritative for writes; other modules request operations.
## Data consumed
Acquisition, ownership-at-event, work and interactions; consume validated snapshots/events rather than reaching into another owner's mutation paths.
## Dependencies
Read interfaces from core modules; financial adapter if selected. Framework/storage/provider choices unresolved.
## Main workflows
Record potential transaction; declare won/lost separately from earnings; aggregate and reconcile.
## Business rules
Unique-customer counts differ from tasks/events; unavailable differs from zero; no commission/payout assumption.
## Validation rules
Validate references, typed inputs, operation identity and applicable expected versions before persistence. Distinguish missing, invalid and unknown values. Do not invent mandatory fields or timing.
## Error conditions
Missing source, invalid formula, zero denominator, currency mismatch. Record safe correlation context and caller action; retry only documented retryable paths.
## Security considerations
Authenticated internal operations; server-side integrity checks; minimal logged customer data. Shared access does not allow impersonation or external CRM disclosure.
## Observability
Operation/event IDs, outcome, policy/schema version and timestamps; redact secrets. Empty result differs from unavailable data.
## Configuration
Only versioned settings applicable to this capability; OQ-008/012 constraints remain explicit.
## Test strategy
Use isolated synthetic fixtures. Verify happy path, invalid references, concurrency where applicable, replay and unavailable dependency. UI loading/empty/error/conflict checks where this module has a screen. No tests executed by this document.
## Open questions
Client conversion, earnings basis, historical attribution and multi-currency.
## Related requirements
REQ-017, REQ-022.
## Related architectural decisions
ADR-001/002 apply where responsibility is consumed; do not reinterpret accepted policies. Proposed module arrangement is PROP-034; detailed implementation remains pending review.
