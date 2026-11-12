# Sales & Marketing CRM — Requirements Baseline v0.1

Date: 13 November 2026  
Working project name: Realstate CRM  
Mode: Requirements consolidation  
Status: Draft for review. Captured requirements reflect the conversation; detailed acceptance criteria, priorities and workflow defaults below are proposed, not approved business policy. This is not an implementation authorization or a finished architecture.

## 1. Product intent and boundaries

Build an internal web application that helps Sales and Marketing manage customer relationships, coordinate responsibility, identify unattended work, automate follow-ups and notifications, and monitor business and team performance. The first business is in real estate; the foundation should be reusable or readily adaptable to other sales organizations.

Confirmed operating scope:

- One shared company workspace initially.
- Real estate agents, Sales and Marketing teams, commission-based personnel, management/performance teams, and customer engagement/support users.
- No restrictive user-group permissions initially. Responsibility and team membership organize work; they do not restrict internal access.
- Individual clients and team/organization shared client pools.
- Customer acquisition from websites, search/social discovery, walk-ins, roadshows, referrals and other manual or automated entry.
- Internal experience takes priority. Public gallery, videos, informational pages and customer profile login are deferred. If introduced later, customers manage only their own profiles and cannot access internal relationships.
- Detailed sales process, commercial model, channels and infrastructure have not been selected.

Business goals (derived from stated needs; numeric targets unknown): prevent missed inquiries and follow-ups; make responsibility visible; support coordinated handovers; reduce repetitive work; connect marketing activity with sales outcomes.

Not committed for the first release: multi-company SaaS operations, customer/partner portals, property inventory management, booking calendars, financial accounting, commission calculation/payouts, AI scoring or autonomous sales agents. Commission-based users do not by themselves imply a commission accounting requirement. The earlier booking-slot proposal was superseded by clarification about client responsibility.

## 2. Classification and source authority

The conversation is the source of truth for this draft. Existing REQ-, PROP-, OQ-, USER-, and SCOPE- identifiers are preserved rather than renumbered. Requirements remain user-stated; acceptance criteria are proposed formulations. Recommendations do not become approved merely because they appear in this document.

Priority proposals for the initial release: Must = central customer/coordination/automation behavior; Should = supporting analytics and refinement. These priorities need review against budget and timeline.

Reference pattern adoption is approved at a functional level. It does not approve every feature in a competitor or every detailed behavior in prior assistant proposals.

## 3. Working vocabulary

| Term | Proposed meaning | Decision still needed |
|---|---|---|
| Contact | A person recorded once, with linked interactions and work | Minimum identity fields and duplicate matching |
| Inquiry | A request or expression of interest linked to a contact | Supported channels and handling statuses |
| Lead / prospect | Sales qualification labels | Whether these are stages, labels or separate records |
| Client | A business relationship classification | Exact qualification or conversion event |
| Opportunity | A particular potential transaction linked to a contact/company | Whether needed in initial delivery; sales stages |
| Responsible person | Person accountable for the relationship | Whether every active client must have one |
| Shared pool | Team or organization queue available for assignment or claim | Claim eligibility, expiry and release rules |
| Task assignee | Person accountable for a particular action | Team-assigned task behavior |
| Handover | Transfer request for a client or task | Acceptance and pending accountability |
| Watchlist | Selected records or saved conditions whose changes matter to a user | Manual following versus dynamic lists |
| Meaningful activity | Interaction or completed action that affects attention status | Exact activity types and clock-reset rules |

Source, introducer, relationship responsibility, task assignment and commission attribution should remain distinct concepts (recommendation). A record being opened is not proposed as evidence that a customer received attention.

## 4. Functional requirement records

Common actor: authenticated internal user unless stated otherwise. All acceptance checks in this section are proposed for review. No exact automation delay or performance target is invented.

### Customer capture and history

**REQ-003 / REQ-004 / REQ-005 / REQ-006 — Capture contacts from multiple routes**  
Classification: user-stated; status: captured; proposed priority: Must.  
Trigger: staff saves a record or an authorized intake integration submits one. Inputs: customer details, acquisition source, submitting user/integration and available referral context. Output: persistent customer record and traceable intake event. External intake connector selection remains open.

Acceptance criteria:

- A staff member can create, retrieve and update a record for a walk-in or referred prospect.
- Website and roadshow/referral records use the same searchable customer repository; a customer login is not required.
- Invalid input is explained without silently discarding entered data.
- An automated intake result records success or failure rather than reporting success before persistence.
- Duplicate candidates are surfaced for review using agreed matching rules; automatic merges are not assumed.

Dependencies/gaps: minimum fields, import sources, duplicate rules and retention. Search and linked interaction history are derived supporting requirements, proposed in FR-001 below.

### Individual responsibility and shared pools

**REQ-014 — Support individual, team and organization client handling**  
Classification: user-stated; status: clarified; proposed priority: Must.  
Trigger: assignment, release or claim. Inputs: client, destination person/pool, acting user and optional context. Output: visible current responsibility and history.

Acceptance criteria:

- Users can distinguish individually assigned records from team/organization pool records.
- An assignment change shows its actor, previous responsibility, new responsibility and timestamp.
- Other internal users can see who currently handles a client without a role-based access barrier.
- If exclusive claiming is adopted, concurrent claims produce one successful claimant and a clear conflict result for the other; silent overwrites are unacceptable.

Proposed behavior: one accountable relationship owner while allowing collaborators. Claim exclusivity and pool membership behavior await approval.

### Collaboration and handovers

**REQ-015 — Coordinate tasks and handovers between positions**  
Classification: user-stated; status: captured; proposed priority: Must.  
Trigger: user assigns work or requests a transfer. Inputs: subject client/task, sender, recipient/team, context, outstanding actions and due date where applicable. Output: visible transfer state and notified participants.

Acceptance criteria:

- A task can be assigned to another person without implicitly transferring client ownership.
- Handover context and remaining work remain attached to the customer/task history.
- Sender, recipient and supervisor can identify pending and completed transfers.
- A failed transfer does not erase the prior responsibility or history.

Proposed states: requested, accepted, declined, cancelled. Proposed default: sender remains responsible until acceptance. This default is not approved; OQ-006 remains open. Client transfer and task transfer require separate actions.

### Attention and supervisory monitoring

**REQ-016 — Identify unattended and actively handled clients**  
Classification: user-stated; status: captured; proposed priority: Must.  
Inputs: responsibility, inquiry status, relevant activity, next action and configured timers. Output: actionable status and explanation.

Acceptance criteria:

- Client views show current responsibility, last relevant activity and next action when present.
- Users can find unassigned records, unanswered inquiries and overdue follow-ups using agreed definitions.
- Each attention alert explains the event/timer that caused it.
- A record with no recorded next action is distinguished from one whose action is overdue.
- Viewing a profile does not silently resolve an overdue customer action.

**REQ-017 — Monitor teams and critical work**  
Classification: user-stated; status: captured; proposed priority: Must.  
Acceptance criteria: a supervisory view can filter by person/team and period; drill down from workload/attention totals to contributing records; identify critical work; assign or assist with work using the same shared internal access model. Supervisor-specific presentation is not a restrictive permission system.

Criticality levels and escalation policy are unresolved. Activity volume must not be presented as proof of sales quality.

### Onboarding, alerts and watchlists

**REQ-018 — Onboarding notification emails**  
Classification: user-stated; status: captured; proposed priority: Must.  
Trigger: agreed onboarding event. Inputs: customer/context, configured recipients and template. Output: email job with visible result.

Acceptance criteria: a qualifying event creates the intended notification; recipients/template are inspectable; failures are visible; repeated processing of the same event does not create duplicate sends. Onboarding milestone, customer versus internal recipients and sender identity remain open.

**REQ-019 — Representative notifications**  
Classification: user-stated; status: captured; proposed priority: Must.  
Acceptance criteria: new inquiries and configured watched events notify the intended current handler/watcher; notifications link to the affected record and explain why they were sent; read/dismissed notification status remains separate from completion of the underlying work. Channel choices and urgent escalation are unresolved.

**REQ-021 — Potential-client watchlists**  
Classification: user-stated; status: captured; proposed priority: Must.  
Acceptance criteria: a user can identify followed potential clients, inspect why a record is watched and stop watching; configured watch events trigger the relevant alert; following a record does not automatically transfer responsibility. Saved dynamic filters are recommended, not yet required.

### Follow-ups and event actions

**REQ-020 — Timed and inactivity-based follow-up**  
Classification: user-stated; status: captured; proposed priority: Must.  
Trigger: specified time, elapsed duration or qualifying inactivity. Inputs: client/task, rule, timing basis, recipients and communication preference. Output: internal reminder or customer communication, explicitly distinguished.

Acceptance criteria:

- An internal user can schedule a reminder and see when it is due.
- An inactivity rule displays which activity types reset its clock.
- Before execution, the system reevaluates current responsibility and stop conditions.
- A reply, opt-out, changed status, reassignment or completed action is handled according to explicit rule policy rather than blindly sending obsolete outreach.
- Failed or delayed execution is inspectable. Retry behavior does not duplicate customer messages.

Proposed first delivery: manual scheduling plus deterministic rules; customer messages only through configured, enabled templates/channels. Quiet hours, time zones, consent preferences, frequency caps and stop conditions need policy decisions.

**REQ-023 — Event-triggered sales/marketing actions**  
Classification: user-stated; status: captured; proposed priority: Must.  
Acceptance criteria: rules expose trigger, conditions and action; users can enable/disable them; executions record matched rule, outcome and errors; disabled rules do not schedule new actions. Proposed controls: preview/test mode, cancellation policy for queued work, loop protection and configuration history. Supported actions/connectors must be bounded before implementation.

### Statistics and reporting

**REQ-022 — Sales and marketing statistics**  
Classification: user-stated; status: captured; proposed priority: Should; baseline reports may be required earlier.

| Requested measure | Required definition/data dependency |
|---|---|
| Spending | Actual versus planned spend; manual input/import/integration; currency and date basis |
| Earnings | Won deal value versus recognized/received revenue; commission versus company income |
| Signups | Registration event and unique-person counting; distinguish staff-entered contacts |
| Engagement | Explicit tracked interactions and instrumentation; unavailable events are not zero |
| Team performance | Assignment history, meaningful activities, response times and outcome definitions |

Acceptance criteria: reports identify period, filters, currency and metric definition; displayed totals reconcile to included source records; missing data appears as unknown/unavailable; source/campaign breakdown is possible where attribution data exists. No ROI claim is valid without a declared formula and consistent cost/revenue data.

### Reusability and shared access

**REQ-001 / REQ-002 / REQ-024 — Shared functional access and adaptable organization**  
Classification: user-stated; status: clarified; proposed priority: Must.

Acceptance criteria: all signed-in internal users can access supported functional work areas initially; personal/team filters change the view rather than create hidden access restrictions; business terminology and sales stages are configurable; industry-specific records do not become mandatory fields for unrelated generic workflows. Exact configurability boundaries remain to be designed.

Proposed organization: Today, Contacts & Relationships, Shared Work, Sales, Marketing, Engagement/Support, Performance and Automation. These are navigation candidates, not approved routes or eight separate applications.

## 5. Derived and recommended foundations

**FR-001 — Searchable customer context (derived, proposed).** Search contacts and inspect linked inquiries, activities, tasks and responsibility changes. Acceptance: a selected client exposes its linked history; empty and failed queries are distinguishable. Search fields and matching are unresolved.

**NFR-001 — Internal authentication boundary (derived, proposed).** Shared internal access does not mean anonymous/public access. Acceptance: unauthenticated requests cannot read/write internal customer records; external intake endpoints validate their allowed operations.

**NFR-002 — Operational traceability (recommended, proposed).** Trace assignment, transfer, important status changes and automation execution to actor/rule and time. Acceptance: inspect who/what changed a record without exposing connector credentials or tokens in history.

**NFR-003 — Reliable scheduled actions (derived, proposed).** Preserve scheduled work across normal application restarts and make delivery outcomes visible. Acceptance: restarting the application does not silently lose a persisted reminder; retrying an execution does not duplicate its logical action. Queue/provider failure behavior needs design.

**NFR-004 — Usable work states (recommended, proposed).** Distinguish loading, empty, validation failure, integration failure and concurrent-edit conflict states in affected journeys. Keyboard use, responsive behavior and measurable accessibility goals remain to be specified.

Performance, concurrency, availability, backup/recovery, data deletion/retention, export, migration, mobile usage, language, currency and time-zone targets are unresolved. No invented numerical service targets are treated as requirements.

## 6. Proposed end-to-end journey

1. Staff or authorized automation captures a roadshow prospect with source/referral context.
2. The system checks duplicate candidates; staff links or creates a contact under agreed rules.
3. The contact enters a shared team pool or receives an individual responsible person.
4. A handler claims or receives the work; others can see that responsibility.
5. The handler records the inquiry, meaningful interaction and next action.
6. A rule sends an onboarding notification or schedules follow-up if its agreed conditions match.
7. A collaborator receives a specific task. A client handover is tracked separately if needed.
8. Inactivity or overdue work appears in attention views and triggers configured reminders/escalation.
9. The handler records the outcome. Qualification/client conversion and opportunity stage changes follow still-to-be-defined rules.
10. Supervisors inspect attention, workload and outcomes; marketing reports use available acquisition/cost data.

This journey is a proposed organizing scenario, not an approved linear lifecycle. Repeat inquiries and multiple opportunities must not require duplicating a person.

## 7. Reference exploration instructions for Claude

Functional pattern reuse was adopted in DEC-001. Study official public interfaces, screenshots, demos and documentation; do not claim signed-in inspection when unavailable.

| Source | Reference focus |
|---|---|
| https://help.followupboss.com/hc/en-us/articles/4422920700439-Lead-Ponds-Moving-Leads-to-a-Pond | Shared pools, claim/release history and notification consequences |
| https://help.followupboss.com/hc/en-us/articles/360034301034-Working-Your-Smart-Lists | Dynamic attention lists based on stages and last communication |
| https://help.followupboss.com/hc/en-us/articles/1500008539982-Action-Plans-Overview | Follow-up sequences, messages and tasks |
| https://support.pipedrive.com/en/article/leads-inbox | Lead work queue and lead-to-deal organization |
| https://support.pipedrive.com/en/article/activities | Daily work and next actions |
| https://support.pipedrive.com/en/article/insights-report-types | Sales/activity report organization |
| https://www.hubspot.com/products/sales | Customer context, sequences and sales workflows |
| https://knowledge.hubspot.com/reports/understand-attribution-reporting | Marketing contribution to contact, deal and revenue outcomes |
| https://help.zoho.com/portal/en/kb/crm/automate-business-processes/assignment-rules/articles/set-assignment-rules | Assignment routing and follow-up work |
| https://help.zoho.com/portal/en/kb/crm/faqs/blueprint/articles/faqs-blueprint | Process states and transitions |

These links were researched in the preceding conversation; no new signed-in UI exploration occurred during baseline generation. Recheck current behavior when using them. Record observed behavior, source, access limitation, proposed adaptation and related requirement. Do not treat product defaults as approved policy. Use an original interface and assets.

Design implementation source: CrisGen UI, https://github.com/crismag/development_design_systems/tree/main/crisgen-ui, requested branch main. Binding comes from the designated project-context instructions. The repository was not inspected for this baseline; resolved commit, compatibility, available components and imports are unverified. Claude must resolve one commit and inspect actual exports/templates before proposing executable usage. Competitor references inform workflows; CrisGen supplies inspected reusable UI building blocks.

## 8. Open decisions and risk register

All business decisions are owned by the product owner; technical evidence collection belongs to the implementing/design agent. Previously open questions are retained.

| Question | Risk | Required decision / impact |
|---|---|---|
| OQ-006 | High | Pending handover accountability; affects task routing, reminders and escalation. Proposed sender-until-acceptance rule remains unapproved. |
| OQ-002 | High | Lead/prospect/client semantics and qualification/conversion; affects records, stages and reports. |
| OQ-008 | High | Onboarding event, recipients, channels, clocks, stop conditions and metric definitions; affects automation correctness. |
| Pool policy | High | Claim versus assignment, release conditions, concurrency and reassignment effects. |
| Data/connectors | High | Existing database, email provider, website/form feeds and tracking access. |
| Reporting | High | Source of spending/earnings, currency and attribution formula. |
| Operations/privacy | High | Hosting, authentication, backup/recovery, retention, deletion and communication preferences. |
| Delivery | Moderate | Budget, timeline, initial users/data volume, devices, stack and team constraints. |
| Special groups | Moderate | Whether any users beyond the five identified groups need distinct workflows. |

Risks: duplicate records can cause duplicate outreach; ambiguous owners can misroute notifications; retries can duplicate sends; unsupported tracking can produce misleading statistics; excessive configurability can enlarge the first release. Resolve through explicit rules and acceptance cases, not undocumented implementation guesses.

## 9. Recommended delivery slices — not implementation tasks

1. Customer capture, search, shared pools, responsibility, activity history and next actions.
2. Reminders, onboarding email, watchlists and a small set of configured event rules with execution history.
3. Handover acceptance, supervisory attention views and escalation.
4. Marketing source/spend data and sales outcome reporting with reconciled metric definitions.

These are proposed sequencing boundaries. Automated customer communications should not be enabled before sender, recipients, delivery policy and stop conditions are defined. No stack, dependency, deployment command or repository structure has been selected.

## 10. Validation and readiness

Review performed: compared this draft to conversational scope; separated user requirements from proposed detail; checked each functional group for observable outcomes and recorded unresolved policy; retained deferred customer scope and rejected booking interpretation.

Not performed: signed-in competitor testing, repository/UI catalog inspection, implementation feasibility against a selected stack, runtime tests, load tests or compliance assessment.

Readiness: suitable for product review and targeted design exploration. Not a complete executable specification. Detailed business rules, data contracts, architecture, module boundaries, interface checkpoints, phased checklist/run log, task bundles and project-specific skills are not generated here. They follow baseline review. The six execution/verification companion documents belong to the later planning/export stage, not this requirements-only deliverable.

Immediate review focus: validate functional scope and resolve handover accountability before detailing ownership-dependent automation. Other unknowns remain recorded and do not prevent independent design exploration.

## 11. Model checkpoint — Commit 17

The permanent identifier record from earlier commits remains authoritative. This file preserves legacy identifiers and adds the following records without renumbering earlier items.

```yaml
model:
  version: 17
  last_commit: 17
  generated: 2026-11-13
project:
  name: Realstate CRM
  working_title: Sales and Marketing CRM
  status: requirements
  project_type: internal tool
  target_platforms: [web]
  downstream_consumers: [product owner, Claude coding agent]
  current_stage: requirements-baseline-review
sources:
  - conversation: user statements and decisions through Commit 16
  - reference_research: official product documentation from preceding turn
requirements:
  user_stated_active: [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-014, REQ-015, REQ-016, REQ-017, REQ-018, REQ-019, REQ-020, REQ-021, REQ-022, REQ-023, REQ-024, REQ-025]
  partial: {REQ-006: internal capture active; customer login deferred}
  deferred: [REQ-007, REQ-008, REQ-009, REQ-010, REQ-011]
  presentation_priority: {REQ-012: internal experience primary}
  clarified: {REQ-013: responsibility coordination, not booking slots}
decisions:
  initial_workspace: one shared company
  internal_permissions: no restrictive role controls initially
  product_references: functional pattern reuse adopted
  customer_area: deferred
actors: [USER-001, USER-002, USER-003, USER-004, USER-005]
open_questions: [OQ-002, OQ-006, OQ-008]
artifacts:
  - name: CRM_Requirements_Baseline_v0.1.md
    classification: proposed baseline
    implementation_ready: false
id_register_additions:
  - {id: FR-001, classification: derived, status: proposed}
  - {id: NFR-001, classification: derived, status: proposed}
  - {id: NFR-002, classification: recommended, status: proposed}
  - {id: NFR-003, classification: derived, status: proposed}
  - {id: NFR-004, classification: recommended, status: proposed}
  - {id: ART-001, classification: requirements baseline, status: draft}
undefined:
  - detailed lifecycle and transfer policies
  - automation channels and timing policies
  - metric definitions and source systems
  - deployment and non-functional targets
  - inspected CrisGen revision and integration
  - architecture, contracts and executable task bundles
```

This is a compact model checkpoint, not the full multi-file context package. Trace from each requirement to source and acceptance criteria is recorded in section 4; architecture/task/test-implementation links remain pending by design.
