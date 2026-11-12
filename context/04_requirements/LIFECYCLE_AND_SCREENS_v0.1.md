# Customer lifecycle and screen organization v0.1
Date: 13 November 2026
ID: PROP-032
Status: proposed for review. Not an approved process, route contract or component inventory.
Sources: requirements baseline, ADR-001, approved PROP-031. Related: REQ-002–006, REQ-014–025, FR-001.
Scope: internal web app, one shared company workspace. All identified internal users can access functions; views organize work without role restrictions.

## 1. Separate concepts instead of separate customer databases
Recommend one contact identity with linked inquiries, opportunities, tasks and interactions. Lead, prospect and client are lifecycle classifications, not copies of the person. A company/business contact can relate to people, but the exact company relationship model remains open.

Keep five dimensions independent:
- Relationship lifecycle: lead, prospect, client.
- Sales opportunity stage: progress of a particular potential transaction.
- Responsibility: individual handler or pool, with approved handover rules.
- Attention: unanswered inquiry, overdue action, missing next action, pending handover.
- Communication preference: channel eligibility and opt-out.

Changing sales stage must not silently change ownership or restart outreach. A client can make another inquiry or have multiple opportunities without becoming a duplicate lead.

## 2. Proposed lifecycle definitions
| Classification | Proposed entry condition | Expected work | Exit/re-entry |
|---|---|---|---|
| Lead | Recorded identity or inquiry; interest not yet qualified | Respond and assess fit, needs and readiness | Qualify to prospect or place in nurture/close interest |
| Prospect | Staff confirms relevant need and a plausible next sales action | Develop a specific opportunity and follow-ups | Become client under agreed conversion policy |
| Client | At least one opportunity meets the company's accepted transaction milestone | Continue service, engagement and future opportunities | Retain client history even when no active sale remains |

The transaction milestone is unresolved: reservation, signed agreement, payment or another business event. Do not equate creating a CRM record with becoming a client.

Nurture, inactive and disqualified should initially be separate engagement/disposition flags with reasons, not mandatory steps everyone must pass through. Archival is a data lifecycle action, not a lost deal. Opt-out is a communication constraint, not a lifecycle classification.

Alternative: configurable free-form labels only. Simpler initially but less consistent for reporting and automation. Recommendation: configurable lifecycle definitions with a small initial set, leaving exact conversion criteria under OQ-002.

## 3. Opportunity progression
Recommended initial example only: New → Qualification → Proposal → Decision → Won/Lost.
Real estate labels such as viewing and reservation may be configured later; they are not mandatory generic stages.
- A lost opportunity does not make every relationship with that person lost.
- A won opportunity is not automatically recognized earnings or cash received.
- Require explicit outcome and date; reasons and required fields remain policy choices.
- Reopening records needs history and a clear counting rule, not duplicate creation.
No stage-duration targets or conversion probabilities are invented.

## 4. Screen organization and user coverage
Screen labels and paths are proposed, not implemented endpoints. All rows inherit shared internal access and exclude customer-facing data exposure.

| Area / section | Primary users | Core work | Requirements | Observable acceptance |
|---|---|---|---|---|
| Today: work queue, attention, upcoming actions | All five identified groups | Review personal/team work, open relevant records, act on reminders | REQ-016, REQ-019, REQ-020 | Overdue, unanswered and pending work remain distinct; totals open matching records |
| Contacts: directory and profile | Agents, sales/marketing, engagement/support | Search, capture, edit, inspect history, interests and next actions | REQ-003–006, FR-001 | Existing record reused for repeat inquiries; source and current handler visible |
| Shared Work: pools, claims, handovers | Agents, commission-based users; supervisors coordinate | Claim clients, request/review release, accept handovers | REQ-014, REQ-015 | Competing claims cannot overwrite; pending sender retains accountability |
| Sales: opportunity list/board and detail | Sales/agents; management | Progress potential transactions and record outcomes | REQ-016, REQ-022; opportunity model proposed | Multiple opportunities link to one contact; won/lost is explicit |
| Marketing: sources, campaigns, watchlists | Marketing; agents contribute | Inspect acquisition and engagement, follow potential customers | REQ-005, REQ-021, REQ-022 | Unknown tracking is distinct from zero; watch does not imply ownership |
| Engagement: inquiries and follow-up history | Customer engagement/support; agents | Respond to inquiries and coordinate service follow-up | REQ-015, REQ-019, REQ-020 | Inquiry has visible response state and next action; full ticketing not assumed |
| Performance: overview, team and source detail | Management/performance; teams inspect own work | Drill into attention, activity and results | REQ-017, REQ-022 | Metrics declare filters/formulas and reconcile to records |
| Automation: rules, templates, execution history | Sales/marketing operations; all internal users initially | Inspect/configure enabled rules and outcomes | REQ-018–023 | Trigger/conditions/actions visible; errors and delivery uncertainty visible |
| Configuration: teams, pools, terminology and stages | Operational users; all internal users initially | Configure agreed business settings | REQ-014, REQ-024 | Labels can change without destroying history; configuration changes recorded |

These are meaningful work sections, not mandated independent modules or deployments. Combine lightweight sections if research shows that reduces navigation. Support uses the same customer history; no separate customer silo.

## 5. Proposed screen behavior
Customer profile: summary and responsibility; next actions; interactions/inquiries; linked opportunities; handovers and history. Source/introducer and current handler have distinct labels. Do not expose commission amounts merely because referral attribution exists.

Shared-work view: pool, coordinator, waiting time, urgency/attention, current state and claim action. Pending releases are not shown as free-to-claim clients. Display conflict refresh rather than silently taking over.

Today view: personal/team selector, prioritized work list and optional summary counts. Notifications support work but are not themselves the definition of completed work.

State requirements for each applicable section:
- Loading must not look like no customers.
- Empty state explains missing records versus filters with no matches.
- Save/validation errors preserve user input.
- Stale assignment conflicts show refreshed responsibility.
- Integration failure distinguishes unavailable data from no activity.
- Unsaved changes and invalid transitions are explained.
- Keyboard/focus, responsive behavior and accessibility targets need design verification; no accessibility certification is claimed.

## 6. Journeys to verify
1. Capture walk-in lead → record inquiry → pool → atomic claim → log response → schedule follow-up.
2. Agent referral → preserve introducer → collaborate on task → accepted handover → retain history.
3. Client submits new inquiry → link existing identity → new opportunity; retain prior relationship.
4. Follow-up overdue → attention flag → handler alert → configured escalation without automatic ownership removal.
5. Agent release → coordinator acceptance → available pool item → new agent claim.
6. No earnings integration → report unavailable data, not fabricated zero revenue.

## 7. Design source and evidence limits
Product pattern references are in the baseline and Claude handoff. No new signed-in UI inspection occurred in this step.
CrisGen UI remains the designated component/template source at https://github.com/crismag/development_design_systems/tree/main/crisgen-ui. A consistent commit and actual APIs/templates must be inspected before screen-to-component selection. This document intentionally names no unverified components/imports.

## 8. Readiness and follow-on artifacts
This is a user/section sketch, not architecture or executable tasks. The later model must register module/user/acceptance IDs and generate the detailed user-module matrix, contracts, hooks/checkpoints, checklist/run log and task-specific skills. No frontend stack, endpoint path, database schema or implementation command is chosen here.

Open: OQ-002 lifecycle semantics/conversion milestone, OQ-008 automation/metrics policies, OQ-010 integrations, OQ-012 delivery constraints, OQ-014 support scope.
Next review: adopt/revise one-contact lifecycle model; independently inspect design source and reference screens.
