# Interface checkpoints
Model 23. No application implementation exists. All procedures proposed; status not_run.
| Checkpoint / acceptance | Interface / hook | Synthetic preconditions | Action and expected evidence |
|---|---|---|---|
| ICP-001 / AT-001 | INT-001 / HOK-001 | Pool client, coordinator, two agents | Concurrent claims: one assignment, conflict for other, stable source attribution; replay does not duplicate |
| ICP-002 / AT-002 | INT-002 / HOK-002 | Sender, recipient, pending transfer | Sender remains accountable before acceptance; recipient acceptance transfers once; wrong accepter/stale request has no writes |
| ICP-003 / AT-003 | INT-003 / HOK-003 | Fixed clock, toured client with no task, overdue task, profile view | No-task client resurfaces; profile view does not reset activity; overlapping reasons deduplicate distinct-client count |
| ICP-004 / AT-004 | INT-004 / HOK-004 | Due action, changed owner/reply, provider stub | Recheck suppresses/reroutes; scheduler replay does not duplicate; timeout recorded uncertain; real provider test separate |
| ICP-005 / AT-005 | Attention/performance UI; concrete hook pending | Overlapping reasons, missing tracking, zero denominator | Count drill-down reconciles; missing is not zero; zero denominator not applicable |

Evidence must identify application commit/working-tree identity, environment, exact check and observed results. Mock provider checks cannot establish real delivery. Browser checks require running app, readiness, URL, role fixtures, selected viewports and keyboard checks; presently not_run because app/toolchain absent. No screenshots or live tests claimed.
