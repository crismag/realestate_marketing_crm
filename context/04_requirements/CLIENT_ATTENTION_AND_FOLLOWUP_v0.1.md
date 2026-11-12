# Client attention and follow-up coverage
Date: 13 November 2026. Model revision: 22.
REQ-026 — User-stated: Help agents managing large client portfolios identify forgotten clients, overdue follow-ups and outstanding tasks through automated reminders and statistics.
Status: captured. Detailed behavior below is proposed under PROP-033.
Extends REQ-016, REQ-017, REQ-019, REQ-020, REQ-021, REQ-022 and REQ-023.
Source scenario: an agent has toured hundreds of clients and can no longer remember who needs attention.

## Outcome
The system actively resurfaces relationships requiring attention, not merely stores contacts or waits for manually created tasks. Include clients with no task at all. A lifecycle label such as client must not hide an ongoing follow-up need. Customer conversion semantics remain open under OQ-002 and do not block this capability.

## Three complementary mechanisms
1. Always-current attention queue inside Today, with customer lists behind each count.
2. Scheduled agent digest summarizing new, continuing and resolved attention items.
3. Event alerts for important changes or due tasks, with configurable escalation.
Frequency, thresholds, channels and escalation targets remain decisions under OQ-008. No production schedules or emails are created by this specification.

## Proposed attention lists
| List | Qualification | Suggested action |
|---|---|---|
| Toured, no follow-up recorded | Completed viewing/consultation with no qualifying later follow-up within configured window | Contact customer or plan next action |
| Inactive relationship | Last qualifying interaction older than configured cadence | Review history and reconnect |
| Next action missing | Active relationship has no actionable future task | Set next step or explicit nurture plan |
| Task overdue | Open task due time passed | Complete, replan with reason, or coordinate |
| Customer awaiting response | Inbound inquiry/reply without linked qualifying response | Respond |
| Promise due | Recorded commitment reaches its due time | Fulfil or explain change |
| Handover waiting | Request remains pending beyond configured window | Recipient reviews; sender remains accountable under ADR-001 |

Viewing/consultation is a configurable activity type, not a mandatory property-booking subsystem. Promise due is an optional proposed task subtype, not a new independent module.

## Evidence and timing
Track outbound attempt, inbound reply, successful conversation, completed meeting/tour and profile view separately. Automated email delivery is not proof of human follow-up or customer response. Opening a profile, changing a tag or dismissing a notification does not reset meaningful-contact inactivity.

Show latest human attempt AND latest successful interaction where known. A missing timestamp means no qualifying recorded history; do not fabricate elapsed duration. Evaluate absence of follow-up after a specific tour as well as general relationship inactivity.

Cadence can depend on lifecycle, relationship type and an explicit next-contact agreement. Do not invent universal 7/14/30-day policy. Respect a future customer-agreed contact date; it may suppress routine inactivity alerts, but must not hide unanswered inbound inquiries or overdue promises. Unrecorded phone contact is a data-quality gap, not proof the agent failed to call.

Store/evaluate timestamps consistently; display agent/workspace timezone. Working hours, holidays and snoozes need agreed policy.

## Actionable cards
Proposed fields: customer, current handler, last tour/consultation, last personal attempt, last conversation/reply, next action/due date, attention reason, time waiting where known.
Actions: open context, record interaction, complete task, create next task, snooze with reason/date, request handover, watch/unwatch.
Snooze changes alert presentation, not historical due dates or evidence of follow-up. Keep snoozed items inspectable.

## Agent statistics
- Assigned active relationships.
- Distinct clients needing attention.
- Toured clients awaiting recorded follow-up.
- Relationships with no next action.
- Tasks due and overdue.
- Unanswered inquiries.
- Clients reached versus attempted.
- Follow-up coverage: distinct eligible clients meeting the declared cadence divided by distinct eligible clients.
Every numerator/denominator must use the same period and filters and link to contributing records. Show missing-history records and exclusions. Counts across categories overlap; do not sum them as unique clients. A zero denominator shows not applicable, not 100% coverage.

Example only, not real data: an agent has 180 clients, 24 have no recent qualifying interaction, 9 toured clients have no follow-up, and 7 tasks are overdue. These values may overlap and must not be added into a fabricated unique total.

## Routing and coordination
Relationship attention targets current responsible agent; pool-held records target the coordinator under ADR-002. Task reminders target task assignees, which may differ from client owner. Pending handover retains sender accountability. Notify recipients about acceptance requests separately.

Separate one customer attention item from the number of open tasks. Reassignment reevaluates routing; queued alerts must not continue repeatedly to a former owner. Watchers may receive configured alerts without acquiring responsibility.

## Notification fatigue and automation
Recommend daily digest as a starting presentation option, not an approved schedule. Group alerts by agent/customer/reason, suppress duplicate notifications for the same evaluation window, and distinguish new attention from continuing backlog. Only send escalation on agreed policies. Clearing notifications alone never completes tasks.

Use persisted rules with inspectable evaluation and execution history. Recompute eligibility before sending. If data/provider unavailable, label failure or unknown; do not silently mark the customer attended or falsely report notification delivery.

Client-facing auto-follow-up is separate from internal prompts. Apply approved communication preferences, stop conditions and frequency controls before customer outreach. Avoid duplicate automated sequences when multiple attention rules match.

## Acceptance scenarios
- Client has a recorded tour but no task: appears in the relevant attention list after configured window.
- Client has a future task but an unanswered inbound inquiry: response-needed indicator remains visible.
- Agent opens the profile: inactivity remains unchanged.
- Automatic email is delivered: human-contact history does not falsely advance.
- Qualifying interaction is logged: affected attention reasons resolve; unrelated overdue tasks remain.
- One client matches three lists: unique attention total counts that client once; reason counts remain three.
- Snoozing a reminder preserves original due/history and resurfaces it at agreed time.
- Ownership changes before digest delivery: recipient is reevaluated.
- Pending handover: sender continues receiving accountability reminders.
- No recorded interaction: show missing history, not an invented last-contact date.
- Metrics drill-down matches displayed count and filters.
- A customer-requested later contact suppresses routine cadence reminders without suppressing urgent responses.
- Duplicate scheduler processing does not duplicate logical notifications.

## Screen impact
Today gains attention lists, coverage summary and digest preferences. Customer profile gains follow-up evidence and next-action status. Performance gains drill-down coverage and aging views. Automation gains cadence/attention rules and evaluation history.
No restrictive roles, customer portal or commission accounting are added. Competitor and CrisGen screen/component research remains outstanding.

## Open decisions
OQ-008: eligible activities, cadence, digest timing, channels, exclusions, working hours, snooze/escalation policies.
OQ-010: which interactions can actually be captured from integrations.
OQ-011: exact metric eligibility and event attribution.
Implementation contracts, UI bindings and checks remain to be designed after policy review.
