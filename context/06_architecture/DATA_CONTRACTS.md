# Data contracts — proposed
Model 23. No application schema, migration history or database exists in inspected repository. This is a candidate domain contract, not an authoritative deployed schema.
Owners: MODULE_BOUNDARIES.md. Select schema authority only after stack decision; persistence/transport/runtime validation/generated types must have explicit mappings.

| Record | Proposed key fields/types | Integrity / unknowns |
|---|---|---|
| Contact | opaque ID; workspace ID; display name string; email/phone nullable; source/referrer references; lifecycle code | Minimum fields and duplicate matching open; never assume email globally unique |
| Inquiry | ID; contact ID; source-event ID nullable; received-at timestamp; response status | Repeat inquiries linked to same identity; reply matching unresolved |
| Assignment | contact ID; responsible kind person/pool; responsible ID; version integer | One current relationship assignment; atomic expected-version transitions |
| Pool | ID; team reference nullable; coordinator user ID; backup nullable | Queue attention needs a recipient; absence coverage open |
| Task | ID; contact ID; assignee; due-at nullable timestamp; status; completion evidence | Client transfer does not silently transfer tasks |
| Handover | ID; subject kind/ID; sender; recipient/person-or-pool; expected version; state; context | Sender accountable until accepted; stale request cannot overwrite later assignment |
| Interaction | ID; contact ID; type; occurred-at; recorded-at; actor/source; external event key nullable | Human attempt/reply/conversation/tour distinct from profile view and email delivery |
| Attention item | ID/key; contact; reason; source references; evaluated-at; policy version; snooze-until nullable | Derived facts; multiple reasons, unique-customer totals |
| Rule/execution | rule ID/version; trigger; conditions; action; logical action key; state; timestamps/error | Persist schedules; distinguish retry attempts and one logical execution |
| Delivery | execution ID; recipient; channel; provider reference nullable; status | Unknown outcome is not success; no secrets stored in payload/log |
| Metric definition | key/version; numerator/denominator/eligibility; date/currency basis; source | Null/unavailable differs from zero; earnings semantics open |

Conceptual ID/string formats, datetime precision, nullable/default rules and enum values require contract approval. Timestamps must preserve actual occurrence versus recording time. Data minimization, archive/delete/retention and backup deletion are open.
Invariant checks before business/UI code: reference integrity, expected-version claim, sender-until-acceptance, stable referral history, distinct activity semantics, idempotent actions and consistent unique counts.
Define validation at external intake, UI/server operations, events and provider callbacks. Static types alone do not validate untrusted input.
Migrations: none yet. Before first migration specify predecessor, isolated DB target, old/new compatibility, backfill, validation queries, deployment ordering, lock/data-loss risks and recovery. Never assume Git rollback reverses migration or sent email.
