# User/module/section matrix
Model 23. Proposed MOD-001–008; actor definitions in ../01_discovery/TARGET_USERS.md.
| Module / section | Primary; secondary users | Actions and boundary | Requirements / acceptance |
|---|---|---|---|
| MOD-001 Contacts / detail | USER-001,002,005;003,004 | Capture/search/edit internal contacts; no public record access | REQ-003–006, FR-001; reuse one identity for repeat inquiry |
| MOD-002 Shared Work / pools | USER-001,003;002,004,005 | Claim, transfer, release; no silent ownership overwrite | REQ-014,015; AT-001,002 |
| MOD-002 Tasks / handovers | All five | Task assignment distinct from relationship responsibility | REQ-015,020; AT-002 |
| MOD-003 Profile / history | USER-001,005;002,003,004 | Log interaction evidence; opening profile is not contact | REQ-016,026; AT-003 |
| MOD-004 Today / attention | All five | Act on distinct reasons; snooze does not rewrite due history | REQ-016,026; AT-003,005 |
| MOD-005 Automation / rules | USER-002;001,003,004,005 | Preview/configure rules; no production sending from docs | REQ-018–023; AT-004 |
| MOD-006 Notifications / templates | All five | Inspect delivery/read status; cannot equate read with completion | REQ-018–020; AT-004 |
| MOD-007 Sales / opportunities | USER-001,002,003;004,005 | Potential transaction progress; lifecycle still proposed | REQ-022; conversion policy open |
| MOD-007 Marketing / Performance | USER-002,004;001,003,005 | Drill into sourced metrics; unavailable data ≠ zero | REQ-017,022; AT-005 |
| MOD-008 Configuration / preferences | USER-002,004;001,003,005 | Configure teams/pools/settings; no restrictive role boundary | REQ-001,024; settings contract pending |

For all UI sections verify loading, empty/filter-empty, invalid input, server failure and stale-data states where relevant. Authentication denial is distinct from internal role access; do not invent role-based forbidden cases.
Each UI implementation slice must load its rows plus its scoped CrisGen reuse records. Full per-screen interaction contracts and accessibility criteria remain pending.
