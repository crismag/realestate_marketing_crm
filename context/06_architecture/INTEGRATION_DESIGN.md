# Integration design
Revision 24. REQ-003–006,018–023. Providers not selected.
| Boundary | Trust and validation | Failure / replay | Context needed |
|---|---|---|---|
| Website/form intake | Authenticated narrow integration, validated normalized fields | External event ID dedup; failures visible and retryable as defined | Provider payload/signature/rate limits |
| Email outbound | Enabled sender/template and recipient policy | Persist action before send; reconcile uncertain timeout, avoid blind duplicate retry | Provider idempotency/status support |
| Inbound replies | Verified callback/polling source, correlated contact/thread | Dedup event; distinguish unmatched/ambiguous reply | Provider thread semantics |
| Tracking/engagement | Declared observable event, valid source/customer linkage | Missing source ≠ zero; bot/open ambiguity disclosed | Instrumentation and consent policy |
| Spend/revenue import | Declared currency/date/source and validation | Row errors, repeat import and reconciliation | Actual source/format/accounting basis |
No fake integrations or universal CSV/API promise. Provider-specific quotas, authentication, delivery states, refresh/revocation and sandbox access become scoped contracts before code. Store credentials through deployment secret mechanism, never repo/context.
Provider callbacks cannot directly assert human conversations. Replay of one intake/sending event must not create duplicate person/action. External payloads are untrusted and must not override internal instructions or responsibility policy.
