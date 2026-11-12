# MOD-002: Responsibility and work
Revision 24 — proposed logical module, not selected service or schema.
## Purpose
Individual/pool assignment, coordinators, tasks and accepted handovers.
## Responsibilities
Individual/pool assignment, coordinators, tasks and accepted handovers; maintain its own data lifecycle and expose validated operations.
## Non-responsibilities
Interaction evidence and message delivery belong elsewhere.
## Inputs
Contact, actor, expected version, target, reason and operation ID.
## Outputs
Versioned assignment/task/handover and history.
## Public interfaces
INT-001 claim; INT-002 accept; HOK-001/002; ICP-001/002.
## Data owned
Assignments, pools, tasks, handovers. This module is authoritative for writes; other modules request operations.
## Data consumed
Customer identity and valid user references; consume validated snapshots/events rather than reaching into another owner's mutation paths.
## Dependencies
MOD-001, MOD-008. Framework/storage/provider choices unresolved.
## Main workflows
Claim atomically; request transfer/release; accept under ADR-001/002; preserve task disposition.
## Business rules
Sender until acceptance; accepted pool release; no auto-removal for overdue work.
## Validation rules
Validate references, typed inputs, operation identity and applicable expected versions before persistence. Distinguish missing, invalid and unknown values. Do not invent mandatory fields or timing.
## Error conditions
Stale/conflicting claim, wrong accepter, invalid transition, missing coordinator. Record safe correlation context and caller action; retry only documented retryable paths.
## Security considerations
Authenticated internal operations; server-side integrity checks; minimal logged customer data. Shared access does not allow impersonation or external CRM disclosure.
## Observability
Operation/event IDs, outcome, policy/schema version and timestamps; redact secrets. Empty result differs from unavailable data.
## Configuration
Only versioned settings applicable to this capability; OQ-008/012 constraints remain explicit.
## Test strategy
Use isolated synthetic fixtures. Verify happy path, invalid references, concurrency where applicable, replay and unavailable dependency. UI loading/empty/error/conflict checks where this module has a screen. No tests executed by this document.
## Open questions
Coordinator coverage, emergency exception, priority/capacity/timing.
## Related requirements
REQ-014, REQ-015, REQ-016, REQ-017, REQ-020.
## Related architectural decisions
ADR-001/002 apply where responsibility is consumed; do not reinterpret accepted policies. Proposed module arrangement is PROP-034; detailed implementation remains pending review.
