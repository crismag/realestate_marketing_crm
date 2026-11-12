# Acceptance catalog
Revision 24. Scenarios proposed except behavior already fixed by ADR-001/002. All runtime evidence not_run.
| Test | Requirements | Given / action | Expected outcome |
|---|---|---|---|
| AT-001 | REQ-014 | Two agents claim one available client | One commits, other conflict; no source/referral overwrite; replay one logical transition |
| AT-002 | REQ-015 | Request/accept/decline/cancel/stale client or pool transfer | Sender until acceptance; coordinator release; wrong recipient/stale request no write |
| AT-003 | REQ-016,026 | Fixed clock and tour with no task; profile view only | Attention appears with reason; profile view not qualifying contact |
| AT-004 | REQ-018–020,023 | Due action replay/reassignment/reply/opt-out/provider timeout | Current policy rechecked; no duplicate logical send; uncertain visible |
| AT-005 | REQ-017,022,026 | Overlapping reasons, absent data and zero denominator | Distinct counts reconcile; unknown not zero; denominator not applicable |
| AT-006 | REQ-003–006, FR-001 | Capture invalid/duplicate/repeat inquiry | Input preserved; duplicate candidate shown; existing identity reused |
| AT-007 | NFR-001 | Anonymous internal operation | Denied server-side, no disclosure/write |
| AT-008 | REQ-021 | Watch then unwatch client; qualifying event | Configured alert stops after unwatch; no ownership change |
| AT-009 | REQ-023 | Preview/disable rule with queued work | Preview no side effect; new actions stop; queued disposition follows explicit policy |
| AT-010 | REQ-024 | Change business labels/stages | Stable identities/history; real estate fields not forced into generic process |
| AT-011 | NFR-003 | Worker/app restart with due reminder | Scheduled work retained; replay safe |
| AT-012 | NFR-004 | Loading/empty/filter-empty/invalid/conflict/provider failure | States distinct, user input retained, actionable recovery |

Browser fixtures and exact viewports/commands must be bound to selected runtime. Integration checks need real storage; real-provider sandbox delivery is separate from mocked adapter checks. Every result identifies tested commit and working-tree identity, clock, policies, environment and evidence.
Coverage limitation: this catalog groups meaningful journeys; it does not assert every detailed baseline criterion has an implemented test. No runtime checks executed.
