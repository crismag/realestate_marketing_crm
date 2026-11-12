# MOD-003: Interaction history
Revision 24 — proposed logical module, not selected service or schema.
## Purpose
Typed real-world contact evidence and provenance.
## Responsibilities
Typed real-world contact evidence and provenance; maintain its own data lifecycle and expose validated operations.
## Non-responsibilities
Attention rules decide whether interaction satisfies cadence.
## Inputs
Contact, actor/source, occurrence/recording timestamps, evidence type.
## Outputs
Linked chronological events and derived facts.
## Public interfaces
Record/list interaction candidates; concrete API pending.
## Data owned
Interaction records and external source-event deduplication. This module is authoritative for writes; other modules request operations.
## Data consumed
Contact/actor identity; consume validated snapshots/events rather than reaching into another owner's mutation paths.
## Dependencies
MOD-001, MOD-008. Framework/storage/provider choices unresolved.
## Main workflows
Log tour, attempt, inbound reply or conversation; deduplicate sourced event; expose last-attempt versus last-conversation.
## Business rules
Profile view and automated email delivery cannot masquerade as human contact.
## Validation rules
Validate references, typed inputs, operation identity and applicable expected versions before persistence. Distinguish missing, invalid and unknown values. Do not invent mandatory fields or timing.
## Error conditions
Invalid type/time, unknown contact, duplicate source event, unavailable source. Record safe correlation context and caller action; retry only documented retryable paths.
## Security considerations
Authenticated internal operations; server-side integrity checks; minimal logged customer data. Shared access does not allow impersonation or external CRM disclosure.
## Observability
Operation/event IDs, outcome, policy/schema version and timestamps; redact secrets. Empty result differs from unavailable data.
## Configuration
Only versioned settings applicable to this capability; OQ-008/012 constraints remain explicit.
## Test strategy
Use isolated synthetic fixtures. Verify happy path, invalid references, concurrency where applicable, replay and unavailable dependency. UI loading/empty/error/conflict checks where this module has a screen. No tests executed by this document.
## Open questions
Qualifying types, corrections/backdated events and provider evidence.
## Related requirements
REQ-016, REQ-020, REQ-026.
## Related architectural decisions
ADR-001/002 apply where responsibility is consumed; do not reinterpret accepted policies. Proposed module arrangement is PROP-034; detailed implementation remains pending review.
