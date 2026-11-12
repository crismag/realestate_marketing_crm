# Error and event catalog
Revision 24. Illustrative conceptual codes, not finalized API statuses.
| Error | Meaning | Caller action |
|---|---|---|
| unauthenticated | No valid internal identity | Authenticate; no data write |
| invalid_input | Payload fails contract | Field-level correction, preserve user input |
| stale_assignment | Expected version differs | Refresh current handler; do not overwrite |
| invalid_transition | Handover/task state incompatible | Explain current state; explicit next action |
| wrong_accepting_identity | Actor is not intended recipient/coordinator | Reject mutation; show appropriate review path |
| unresolved_pool_accountability | No usable queue coordinator | Retain sender; configure/resolve recipient |
| persistence_unavailable | State not committed | Report failure; safe idempotent retry |
| provider_unavailable | Definite delivery failure | Retry under policy; assignment unaffected |
| delivery_uncertain | Provider outcome not known | Reconcile, not blind resend |
| data_unavailable | Missing source/measurement | Display unavailable/freshness, not zero |

Event candidates: contact captured, inquiry received, assignment claimed, handover requested/accepted/declined/cancelled, release accepted, interaction recorded, task scheduled/completed/rescheduled, attention evaluated, logical action scheduled, delivery outcome recorded.
Each event needs stable ID/version, occurrence/recording time, subject/workspace, actor/source and correlation. Minimal payload; no secrets. Different events may arrive out of order; handlers use current state/version. Audit facts and event transport are distinct storage responsibilities to finalize.
