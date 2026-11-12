# MOD-004: Client attention
Revision 24 — proposed logical module, not selected service or schema.
## Purpose
Explainable missing-follow-up detection and queue projections.
## Responsibilities
Explainable missing-follow-up detection and queue projections; maintain its own data lifecycle and expose validated operations.
## Non-responsibilities
Cannot reassign clients or send messages directly.
## Inputs
Current responsibility/tasks, typed interactions, as-of time and versioned cadence.
## Outputs
Distinct customer attention and reason items with freshness.
## Public interfaces
INT-003/HOK-003/ICP-003; ICP-005 count checks.
## Data owned
Derived attention projection, evaluation/snooze history. This module is authoritative for writes; other modules request operations.
## Data consumed
MOD-001/002/003 facts; MOD-008 cadence; consume validated snapshots/events rather than reaching into another owner's mutation paths.
## Dependencies
MOD-001, MOD-002, MOD-003, MOD-008. Framework/storage/provider choices unresolved.
## Main workflows
Evaluate toured-no-followup, no-next-action, unanswered and overdue; dedup customer totals; expose reason drilldown.
## Business rules
Include clients with no task; snooze preserves original due history; unknown source is not zero.
## Validation rules
Validate references, typed inputs, operation identity and applicable expected versions before persistence. Distinguish missing, invalid and unknown values. Do not invent mandatory fields or timing.
## Error conditions
Invalid policy, unavailable facts, stale projection; show freshness. Record safe correlation context and caller action; retry only documented retryable paths.
## Security considerations
Authenticated internal operations; server-side integrity checks; minimal logged customer data. Shared access does not allow impersonation or external CRM disclosure.
## Observability
Operation/event IDs, outcome, policy/schema version and timestamps; redact secrets. Empty result differs from unavailable data.
## Configuration
Only versioned settings applicable to this capability; OQ-008/012 constraints remain explicit.
## Test strategy
Use isolated synthetic fixtures. Verify happy path, invalid references, concurrency where applicable, replay and unavailable dependency. UI loading/empty/error/conflict checks where this module has a screen. No tests executed by this document.
## Open questions
Cadence/eligible clocks, exclusions, snooze and working hours.
## Related requirements
REQ-016, REQ-017, REQ-026.
## Related architectural decisions
ADR-001/002 apply where responsibility is consumed; do not reinterpret accepted policies. Proposed module arrangement is PROP-034; detailed implementation remains pending review.
