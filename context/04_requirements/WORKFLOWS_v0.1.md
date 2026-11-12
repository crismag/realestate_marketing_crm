# Workflow proposal v0.1
Classification: mixed. ADR-001 handover accountability is approved; other workflow details remain proposed. Source: baseline REQ-014 through REQ-023. No production automation is authorized by this document.

## 1. Ownership and task responsibility
A contact is a durable customer identity. Relationship responsibility is either a named person or a named shared pool. A separate task can belong to a different person without changing the relationship owner. Referral attribution remains independent.

Recommended exclusive claim operation:
- Input: record, current assignment version, acting user.
- Preconditions: record remains in the requested pool; user is an authenticated internal user.
- Success: atomically assign the record and append responsibility history.
- Conflict: another assignment won; return the current handler, with no silent overwrite.
- Unknown: pool eligibility rules and release/expiry policies.

Acceptance scenario: two agents claim the same pool record simultaneously; exactly one becomes responsible and the other sees the conflict and current handler.

## 2. Handover proposal
Recommended states: requested → accepted, declined or cancelled. A requested handover does not itself change the existing owner. Acceptance transfers responsibility atomically and records sender/recipient/context. Decline/cancellation retains the current owner. A request becomes stale if responsibility changes before acceptance; require review instead of overwriting newer assignment.

**ADR-001 — Approved 13 November 2026:** The sender remains responsible until the recipient explicitly accepts the handover. OQ-006 is resolved. Pending-handover responsibility-based reminders continue to target the sender; the recipient may receive acceptance-request notifications. Acceptance changes accountability; merely requesting a transfer does not. Timing/escalation and whether supervisors may force transfer remain open.

Separate task handover from client handover. Do not implicitly transfer all tasks. Show outstanding tasks during client transfer and require an explicit disposition for each affected task.

Acceptance scenarios:
- Requested transfer remains visible to sender, receiver and supervisor.
- Acceptance of a stale request cannot overwrite a newer owner.
- A failed transfer leaves prior responsibility intact.
- Repeated acceptance produces one logical transfer.
- Cancelling a handover does not delete its history.

## 3. Attention signals
Use independent indicators rather than one misleading 'active' status:
- Unassigned / pool waiting.
- Inquiry awaiting response.
- Next action missing.
- Action overdue.
- Inactivity threshold exceeded.
- Handover awaiting acceptance.
- Critical task flagged.

Show the reason and relevant timestamp. Being on a watchlist or opening a profile is not evidence of customer contact. Outbound attempts, inbound replies and successful conversations should remain distinct activities; which resets an inactivity clock is configurable and unresolved.

Acceptance: a customer can simultaneously have a responsible agent and an overdue task; assignment alone does not clear the overdue indicator.

## 4. Automation lifecycle
Proposed conceptual flow: event or timer → evaluate rule → schedule action → recheck current state → execute → record outcome.
Execution outcomes: scheduled, running, succeeded, failed, cancelled/skipped, and delivery-uncertain when a provider result cannot be determined. These are design proposals, not fixed database enums.

Each logical action needs an idempotency key, originating event/rule version, target record and execution history. Recheck responsibility, reply state, opt-out, completion and applicable schedule rules before sending. An uncertain provider timeout must not cause blind duplicate outreach; reconcile with the provider where supported or flag for review.

Rules distinguish internal notification, task creation and customer email. Read/dismissed notifications do not resolve underlying work. Disable semantics for already queued actions must be decided explicitly.

Acceptance scenarios:
- Replayed intake event does not duplicate onboarding email.
- A customer reply before a scheduled follow-up causes the rule's stop policy to be applied.
- Reassignment before execution selects recipients under the documented routing policy.
- Worker restart preserves persisted reminders.
- Unavailable email provider produces a visible failure/uncertain result, not false success.
- Missing tracking data is reported as unavailable, not no engagement.

## 5. Supervisory view
Proposed operational filters: person, team/pool, date range, source and attention reason. Drill into source records behind counts. Supervisor labels provide presentation and responsibility, not restrictive permissions in this release. Do not automatically reassign unattended clients until reassignment policy is accepted.

## 6. Workflow choices
A. Direct reassignment: simpler, but recipients can receive unexpected responsibility.
B. Acceptance-based handover: explicit accountability, but creates pending work to monitor.
Selected: acceptance-based accountability for client handovers (ADR-001). Explicit supervisor override remains a separate open policy; this approval does not approve unrelated workflow defaults.

Approved-rule acceptance checks:
- Requesting a handover leaves the sender responsible.
- Explicit recipient acceptance transfers responsibility.
- Decline or cancellation leaves sender responsibility unchanged.

Next: define lifecycle terminology and shared-pool rules.
