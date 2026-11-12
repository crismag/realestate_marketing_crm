# Security and data lifecycle
Revision 24. Proposed controls, not compliance certification.
Contact and interaction data are internal business records. All internal groups initially share functions; authentication still separates public visitors from staff. No production records belong in this public repository.
Protect acceptance identity, expected assignment version, validated payloads and secret boundaries server-side. Shared role access does not authorize impersonating another recipient's acceptance.
Lifecycle proposal: create/validate → update with history → archive with discoverable reason → delete under agreed retention/legal policy. Archive must not imply opt-out; deletion must account for linked jobs, provider records, logs and backups. Exact retention and legal obligations are unknown.
Data minimization: capture only fields needed for customer work, avoid sensitive free-text notes and redact secrets in errors. Exports/imports need access validation, safe formatting and history. Automated messages honor communication preferences and current suppression policy.
Recovery: encrypted/controlled backups appropriate to selected host, periodic restore evidence, declared RPO/RTO. Neither encryption specifics nor restore command is chosen without infrastructure.
Security check execution is in ../09_development/SECURITY_VERIFICATION_MATRIX.md. Implementer must assess session/CSRF/CORS, injection, output encoding, webhook validation and rate limits for actual boundaries; do not assert controls merely because this document names them.
