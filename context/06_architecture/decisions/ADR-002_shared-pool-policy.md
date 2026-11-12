# ADR-002: Exclusive claims and accepted pool release
## Status
Accepted by product owner, conversational Commit 21, 13 November 2026.
## Context
Clients may be individually handled or in shared queues, with overlapping agent work.
## Decision
Manual atomic exclusive claim; coordinator-accepted release to pool; overdue alerts/escalation without automatic ownership removal. Pool coordinator covers queue attention after accepted release until an agent claims.
## Alternatives
Immediate self-release risks unowned attention. Automatic recycling may disrupt ongoing relationships. Round-robin adds routing complexity; manual claims adopted initially.
## Consequences
Transparent handler and collision prevention; coordinator queue workload and coverage must be managed. Task assignment/referral/commission attribution remain separate. Capacity, sort priorities, emergency overrides and timing are unresolved.
## Supporting requirements
REQ-014, REQ-015, REQ-016, REQ-017. Scope/details: ../../04_requirements/SHARED_POOL_POLICY_v0.1.md.
