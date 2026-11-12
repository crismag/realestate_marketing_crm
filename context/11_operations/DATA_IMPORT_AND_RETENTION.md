# Data import and retention planning
Revision 24. Proposed, no source database selected.
Discover existing source/export, record count, identity quality, contact preferences and provenance before choosing import format. Preserve source ID, source event and import-batch references. Map fields/stages explicitly; preview errors/duplicates before applying.
Imports must not reset follow-up clocks, generate customer onboarding messages or change attribution by default. Enable those side effects only with reviewed migration policy. Repeat batch should not duplicate identity/events.
Validation: synthetic sample, malformed fields, duplicate candidates, existing client match, partial failure, replay and reconciliation totals. Do not auto-merge based on shared phone/email without accepted policy.
Retention/archive/delete and backup/provider cleanup remain OQ-012. Deletion impacts pending actions and reporting; define legal hold and historical aggregate policy if applicable. No real customer export or secret belongs in this repository.
