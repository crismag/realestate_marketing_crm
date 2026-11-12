# Proposed logical module boundaries
Model revision 23. PROP-034: proposed, not approved architecture. No runtime/stack selected.
Recommendation: bounded capabilities inside one application initially, with durable background execution where needed. Alternative: independently deployed services; defer because team/scale constraints do not justify that operational cost yet. Pure synchronous sending is simpler but cannot reliably cover inactivity timers and retries. Deployment choice remains open.

| Module | Owns | Consumes | Requirement links |
|---|---|---|---|
| MOD-001 Customer relationships | Contact identity, acquisition/referral context, inquiry records, relationship classification | Team/person references | REQ-003–006, REQ-024, FR-001 |
| MOD-002 Responsibility and work | Assignment version/history, pools/coordinators, tasks, handover lifecycle | Contact identity | REQ-014–017, ADR-001, ADR-002 |
| MOD-003 Interaction history | Typed interaction evidence, timestamps, source event deduplication | Contacts, people | REQ-016, REQ-020, REQ-026 |
| MOD-004 Attention | Derived reason items, evaluation history and snooze state | Assignments, tasks, interactions, configured cadence | REQ-016, REQ-017, REQ-026 |
| MOD-005 Automation | Rule versions, persisted schedules/executions and action orchestration | Events and current domain snapshots | REQ-018–023 |
| MOD-006 Communications | Notification deliveries/read state, templates, channel adapters and communication preferences | Action intents, recipient/current routing | REQ-018–020 |
| MOD-007 Sales and marketing measurement | Proposed opportunities, campaign/spend entries and metric definitions/read models | Acquisition, work, interactions and declared financial inputs | REQ-022 |
| MOD-008 Organization configuration | Users, teams, lifecycle/cadence settings and functional configuration | Selected auth identity provider | REQ-001, REQ-002, REQ-024 |

These are ownership boundaries, not eight databases/services. Only the owning module mutates its records. Cross-module writes use explicit operations; reporting does not write assignment state. Attention reads facts but cannot reassign a customer. Communications reports delivery outcomes but cannot mark a successful conversation. Automation invokes owning operations rather than directly editing their storage.

Dependency direction: core contact/configuration references → responsibility/interactions → derived attention → automation orchestration/communications → reporting projections. Avoid callback cycles: publish outcomes as domain events, do not have email adapter synchronously call CRM mutation code. Event persistence/transport and transaction strategy remain unresolved.

Proposed event envelope: event ID, type/version, occurred-at, workspace, subject ID, actor/source, correlation ID, minimal payload. Never place provider secrets in events. Ordering and replay guarantees must be specified per contract; no global exactly-once claim.

System boundary: authenticated internal UI → validated application operations → persistence and durable jobs → configured external providers. External intake is a narrow validated integration, not public CRM read access. Customer portal and multi-company SaaS remain deferred.

Failure principles: reject invalid/stale assignment transitions without side effects; preserve a committed assignment when its notification fails; surface capture failures; distinguish unknown delivery from definite failure; record retries separately from logical actions. Real-time updates versus refresh/polling remains a design choice.

Data ownership, interface candidates and user coverage are expanded in companion files. Exact schemas, routes, endpoints, hosting, auth and workload constraints remain open; no implementation is ready solely from this index.
