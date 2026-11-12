# Shared client pool policy v0.1
Date: 13 November 2026
ID: PROP-031
Classification: recommended; approval pending under OQ-009.
Related requirements: REQ-014, REQ-015, REQ-016, REQ-017, REQ-019, REQ-020.
Approved constraint: ADR-001 — sender retains responsibility until recipient explicitly accepts a handover.

## Recommended operating model
A pool is a shared queue of customer relationships awaiting an individual handler. Claiming assigns accountability; it does not hide the client from colleagues or establish commission entitlement. Team membership supports organization and routing, not restrictive access in this release.

| Operation | Recommended rule | Visible result |
|---|---|---|
| Enter pool | Select destination pool; preserve source and referral attribution | Pool, waiting-since time, previous responsibility |
| Claim | First successful server-side atomic claim wins | Current agent and assignment time visible to everyone |
| Concurrent claim | Reject stale/conflicting request; return current assignment | Explain who claimed it; no silent overwrite |
| Collaborate | Assign tasks or add collaborators without taking relationship ownership | Each task has an accountable assignee |
| Direct transfer | Use recipient-acceptance handover under ADR-001 | Sender stays responsible while pending |
| Release to pool | Require reason, next-action context and review of outstanding tasks | Available in pool; history retained |
| Inactivity | Flag and notify; do not automatically remove ownership initially | Current handler and supervisor can act |
| Supervisor action | Coordinate reassignment through the same handover rules | Recorded actor, reason and outcome |

No holding a client just by opening its record. No automatic ownership expiry, automatic recycling or automatic commission change in the initial proposal.

## Pool accountability — gap that must remain visible
A pool-held client has no individual sales handler. Recommend a named pool coordinator (and optional backup) to receive unattended-inquiry alerts until someone claims it. The coordinator role is operational accountability, not an access permission.

Pool coordinator selection, absence coverage and whether new pool items notify all team members or only the coordinator remain proposed. If no coordinator is configured, show the routing gap; do not report an alert as delivered to nobody. A team/organization name alone cannot receive a personal notification.

## Release is a handover, not an accountability escape
To preserve ADR-001, recommend treating release from an individual to a pool as a handover accepted by that pool's coordinator. Until acceptance, the current agent remains responsible and the client is not claimable as a free pool item. After acceptance, the coordinator covers pool-level attention until an agent claims it.

An alternative is immediate self-release to a pool; it is simpler but creates a gap unless pool accountability is established. Recommendation: coordinator-accepted release. This extra pool acceptance policy is NOT yet approved by approval of ADR-001.

No blanket supervisor force-transfer exception is assumed. Emergency override behavior is a separate unresolved decision, not a hidden bypass.

## Outstanding work
Client ownership changes must not silently reassign all tasks, cancel reminders, restart sequences or change introducer attribution. Before release/transfer show:
- Open inquiries and time-sensitive actions.
- Tasks and their existing assignees.
- Pending handovers.
- Scheduled communications whose routing might change.

Task assignees stay unchanged unless explicitly transferred. For relationship-based notifications reevaluate the current responsible person at execution; task-specific reminders continue to their task assignee. Client-message sender identity must follow a separately defined communication policy.

## Conceptual states
- Pool available: coordinator accountable for queue attention; agent can claim.
- Individually assigned: named agent accountable.
- Transfer pending: existing agent accountable; recipient sees acceptance request.
- Release pending: existing agent accountable; coordinator sees acceptance request.

Accepted transfer/release, decline and cancellation remain historical events, not extra active ownership states. No timeout silently completes a pending handover. A stale request must be reviewed if assignment changed.

## Proposed operation contract
Illustrative, not fixed API or database schema:
Input: operation ID, customer ID, expected assignment version, actor ID, destination where applicable, reason/context.
Success: current assignment, new version, recorded transition and notification outcome.
Errors: unauthenticated, invalid destination, stale assignment, already claimed, unresolved pool accountability, persistence unavailable.
Mutations use atomic version checks. Retry the same operation ID without producing a second transition. If notifications fail after assignment succeeds, preserve the assignment and retry/report notification separately.

## Acceptance cases
1. Two agents claim the same available record: one succeeds, one sees the current agent.
2. An agent opens an unclaimed record: it stays available until a claim succeeds.
3. Claiming a client does not remove other internal users' visibility.
4. A pending person-to-person transfer leaves the sender accountable.
5. A requested pool release leaves the sender accountable until coordinator acceptance.
6. Declined/cancelled pool release leaves assignment intact.
7. A stale release cannot overwrite an intervening accepted handover.
8. Repeating an accepted claim or release does not duplicate transitions/notifications.
9. A follow-up becomes overdue: flag/escalate, retain ownership.
10. A colleague completes an assigned task: client ownership remains unchanged.
11. A successful assignment with failed notification remains assigned and exposes delivery failure.
12. Referral/commission attribution is unaffected by claim, release or assistance.

Cases 5–6 depend on acceptance of the proposed coordinator-release model. Escalation periods, response targets and inactivity definitions remain open under OQ-008; no numerical defaults are specified.

## Priority and fairness
Initial recommendation: transparent manual claiming, with waiting-since and attention indicators. Queue order prioritizes explicitly flagged urgent work, then longest waiting within the same priority; final sorting and priority levels need review. Client value should not silently overrule overdue attention.

Round-robin routing, availability/capacity limits and recycling can follow after real workload is understood. Do not implement them merely because reference products offer them.

## Review decision
Approve or revise: manual exclusive claim, coordinator-accepted release, overdue alerts without automatic ownership removal.
Next independent design work: lifecycle terminology and a screen/module map; preserve unresolved rules locally in affected context.
