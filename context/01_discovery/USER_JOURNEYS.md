# User journeys
Revision 24. Proposed interaction detail; ADR-001/002 are approved.
| Journey | Start / actor | Main path | Alternate/failure path | Done evidence |
|---|---|---|---|---|
| Capture | Walk-in/referral; agent | Find existing contact → link/create → inquiry/source → next action | Duplicate candidate or invalid fields; preserve input | Searchable one identity and intake history |
| Claim | Pool client; agent | Inspect context → claim → see handler and task | Simultaneous claim loses with current assignment shown | AT-001 |
| Tour follow-up | Logged tour; agent | Record outcome → next task or configured cadence → attention queue | No task still resurfaces; external contact may be missing | AT-003 |
| Handover | Assigned client; sender/recipient | Request with context → recipient accepts → responsibility changes | Decline/cancel/stale; sender remains responsible | AT-002 |
| Pool release | Assigned client; sender/coordinator | Request → coordinator accepts → available pool → new claim | Missing/absent coordinator flagged; no silent responsibility loss | AT-002 |
| Reminder | Due task/attention; worker/agent | Evaluate → recheck → notify → act | Reply/opt-out/current owner changed; skip/reroute per policy | AT-004 |
| Supervisor | Team backlog; manager | Filter → drill down → assist/coordinate → inspect outcomes | Unknown metrics/data freshness explicit | AT-005 |
| Repeat sale | Existing customer; sales | Reuse contact → new inquiry/opportunity → record outcome | Do not overwrite earlier transaction/history | Lifecycle milestone still open |
No journey requires customer login. Viewport/device, working hours and full support-case journey remain unresolved.
