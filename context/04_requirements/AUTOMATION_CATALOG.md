# Proposed automation catalog
Model 23. PROP-035. Detailed rules proposed; thresholds/channels remain OQ-008.
All rows require inspectable trigger/conditions, enabled version, recipient resolution, stop policy, idempotency and outcome history. No rule is a live scheduled automation.

| Local key | Trigger and condition | Action / recipient | Stop or recheck | Requirements |
|---|---|---|---|---|
| onboard | Agreed onboarding milestone reached | Enabled onboarding email to explicitly configured recipient | Existing execution, preference, current milestone | REQ-018 |
| inquiry | Valid inquiry persisted | Notify current handler or pool coordinator | Duplicate event, assignment change | REQ-019 |
| after-tour | Completed tour/consultation and configured window passed without qualifying follow-up | Attention item, handler reminder | Later qualifying activity; agreed future contact | REQ-026 |
| inactivity | Configured meaningful-contact clock exceeded | Attention queue and internal reminder | Current activity, suppression, routing | REQ-020, REQ-026 |
| missing-next | Eligible active relationship has no next action | Prompt responsible agent/coordinator | New next action; disposition | REQ-016, REQ-026 |
| task-due | Task reaches due time or overdue policy | Task assignee reminder | Completion, changed due date, deduplication | REQ-020 |
| handover | Requested transfer or configured pending duration | Recipient acceptance request; sender accountability reminder | Accepted, declined, cancelled, stale request | REQ-015, REQ-019 |
| pool-release | Requested release to pool | Coordinator review notification | Current sender retained until acceptance | ADR-002 |
| watch | Configured event on watched record | Watcher alert | Unwatch, duplicate event, changed preference | REQ-021 |
| digest | Configured schedule with current attention matches | Grouped personal/team digest | Reevaluate counts, recipient and unresolved backlog | REQ-026 |
| escalation | Agreed unresolved-work threshold | Configured supervisor/coordinator alert | Resolution, previous escalation, ownership change | REQ-017 |
| customer-followup | Explicitly enabled customer sequence step | Approved customer template/channel | Reply, opt-out, invalid address, frequency, quiet hours, status | REQ-020, REQ-023 |

Proposed operational controls: draft/test/enable/disable rules; preview matches without sending; inspect rule version and delivery log; explicitly decide whether disabling cancels queued actions; distinguish pause/snooze/stop. Preview has no side effects.
A logical action key includes originating event/evaluation window, rule/version, target and action step. Separate notification read status from underlying task completion. Scheduler replay cannot multiply logical actions.
Financial statistics need source data, not an automation that fabricates earnings from a won deal. Tour logging does not require a booking subsystem. No AI is necessary for this deterministic baseline.
