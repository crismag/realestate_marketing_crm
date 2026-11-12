# Proposed metric dictionary
Revision 24. REQ-017,022,026. Formula definitions need owner review.
| Metric | Proposed calculation | Caveat |
|---|---|---|
| Clients needing attention | Distinct eligible contacts with ≥1 active reason | Do not sum overlapping reason counts |
| Missing next action | Eligible active relationships with no actionable next task/plan | Nurture exclusions declared |
| Follow-up coverage | Distinct eligible contacts meeting declared cadence / eligible contacts | Zero denominator = not applicable; missing history disclosed |
| Inquiry response time | First linked qualifying response timestamp minus inquiry timestamp | Automated acknowledgment versus personal response distinct; unresolved inquiries separate |
| Overdue tasks | Open tasks past due as of report time | Show original and rescheduled due context |
| Signup count | Unique explicit registration events/person rule | Manual intake is not automatically signup |
| Acquisition count | Captured contacts by declared acquisition rule | Reimports and duplicate merges must not inflate |
| Spend | Sum actual eligible spend entries in declared currency/period | Planned spend separate; conversion source needed |
| Won value | Sum won opportunity amount under declared close-date basis | Not cash received or recognized revenue |
| Earnings | Owner-defined recognized/received income | Unavailable until financial source adopted |
| Engagement | Named interaction counts by type/source | Missing instrumentation = unavailable, not zero |

Every report includes period/timezone, filters, definition version, freshness, missing-data count and drill-down. Historical team performance should state whether attributed to event-time handler or current team; never silently substitute one. Monetary precision and currency conversion policy unresolved.
Task counts, customer counts and unique event counts are different units. No inferred ROI/profit or conversion rates without declared denominator and source evidence.
