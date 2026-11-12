# ADR-001: Sender accountability until accepted handover
## Status
Accepted by product owner, conversational Commit 19, 13 November 2026.
## Context
Shared work crosses positions; responsibility must not disappear while a recipient has not acted.
## Decision
Sender remains responsible until explicit recipient acceptance. Decline or cancellation retains current sender responsibility.
## Alternatives
Immediate reassignment is simpler but can impose unseen work. Shared ambiguous ownership weakens accountability. Neither was selected.
## Consequences
Clear accountability and reminders; pending handovers need visibility and follow-up. Correct accepting identity/stale-state validation is required. Timeout/escalation/force override are not approved by this decision.
## Supporting requirements
REQ-015, REQ-019, REQ-020. Detailed workflow: ../../04_requirements/WORKFLOWS_v0.1.md.
