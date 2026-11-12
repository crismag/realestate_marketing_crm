# Operations and deployment context
Revision 24. No platform chosen; no deploy/start/rollback commands verified.
Resolve: expected users/volume, budget, operator ownership, host restrictions, region, email provider, service availability and backup targets.
Minimum operational capabilities proposed: health/readiness per app/worker; pending/late job visibility; failed/uncertain delivery queue; policy evaluation errors; stale integrations; backup/restore evidence; configuration version history.
Logs need correlation/action IDs and safe error classification; no customer message bodies or secrets by default. Metrics may measure queue age and execution outcomes; thresholds need agreement.
Release order: compatible schema/contracts → application/worker → isolated smoke/journey evidence → scoped pilot. Destructive migration and production send enablement require explicit authorized scope; documentation generation does not authorize deployment.
Rollback app code separately from schema/backfill/provider side effects. Record current revision, pending jobs and recovery point. Select Git revert/forward fix according to actual state, never automatic destructive cleanup.
A pilot should use synthetic then explicitly authorized real data and approved send rules. Availability and recovery promises remain open; no SLA invented.
