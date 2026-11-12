# MOD-006: Communications
Revision 24 — proposed logical module, not selected service or schema.
## Purpose
Delivery adapters, templates, preferences and notification read state.
## Responsibilities
Delivery adapters, templates, preferences and notification read state; maintain its own data lifecycle and expose validated operations.
## Non-responsibilities
Cannot change sales lifecycle/ownership or mark human conversation.
## Inputs
Logical action identity, allowed template/channel and resolved recipient.
## Outputs
Outcome/provider correlation, visible notification and failure.
## Public interfaces
INT-004/HOK-004/ICP-004.
## Data owned
Delivery attempts, template versions, preferences/read state. This module is authoritative for writes; other modules request operations.
## Data consumed
Current routing and enabled action intent; consume validated snapshots/events rather than reaching into another owner's mutation paths.
## Dependencies
MOD-008 configuration and provider adapters; consumes owning-domain snapshots. Framework/storage/provider choices unresolved.
## Main workflows
Resolve recipient; validate current suppression; send once/reconcile; expose status and separate read flag.
## Business rules
Read is not work completion; delivery is not response; no blind resend on unknown timeout.
## Validation rules
Validate references, typed inputs, operation identity and applicable expected versions before persistence. Distinguish missing, invalid and unknown values. Do not invent mandatory fields or timing.
## Error conditions
Invalid recipient, definite provider failure, uncertain outcome, suppression. Record safe correlation context and caller action; retry only documented retryable paths.
## Security considerations
Authenticated internal operations; server-side integrity checks; minimal logged customer data. Shared access does not allow impersonation or external CRM disclosure.
## Observability
Operation/event IDs, outcome, policy/schema version and timestamps; redact secrets. Empty result differs from unavailable data.
## Configuration
Only versioned settings applicable to this capability; OQ-008/012 constraints remain explicit.
## Test strategy
Use isolated synthetic fixtures. Verify happy path, invalid references, concurrency where applicable, replay and unavailable dependency. UI loading/empty/error/conflict checks where this module has a screen. No tests executed by this document.
## Open questions
Provider, sender identity, recipients, consent/quiet-hours policy.
## Related requirements
REQ-018, REQ-019, REQ-020.
## Related architectural decisions
ADR-001/002 apply where responsibility is consumed; do not reinterpret accepted policies. Proposed module arrangement is PROP-034; detailed implementation remains pending review.
