# Operator runbook — draft
Revision 24. Actual services/commands/owners unknown.
## Missed reminder
Inspect task due/policy/timezone, scheduler state, last evaluation, recipient resolution, suppression and delivery outcome. Do not blindly resend uncertain messages. Preserve action/correlation evidence.
## Unexpected attention
Inspect recorded versus occurred time, eligible interaction types, later agreed contact date, snooze, missing data and current policy version. Correct facts with history; do not mark communication completed solely to clear metrics.
## Conflicting ownership
Inspect expected assignment version and accepted handover history. Refresh state; no force overwrite or unlogged manual DB edit.
## Email/provider failure
Distinguish invalid recipient, definite rejection and unknown timeout. Check provider status under authorized tooling; retry only within policy. Credential changes never go into logs/context.
## Data recovery
Use selected environment restore procedure and invariant checks. Git rollback does not undo migrations/messages. Verify test target before destructive seed/reset.
## Handoff
Record symptom, scope, current revision/environment, observed evidence, actions attempted, unresolved risk and next responsible operator. Production escalations and recovery targets require owner agreement.
