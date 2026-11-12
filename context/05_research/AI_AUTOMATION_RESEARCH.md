# AI and automation research: reference CRMs

Status: **research and proposals only**. Nothing here is approved, built or scheduled. AI is out of
first-release scope in the PRD; every AI-assisted item below is a proposal for Cris to accept, defer or
reject through **OQ-015** in `../04_requirements/OPEN_DECISIONS.md`.

- Researched: 2026-11-12 (UTC), TASK-002 reference portion, against `main` at f59c420 (CRM build merged).
- Method: public vendor documentation and product pages only, read anonymously. No signed-in UI, trials,
  screenshots, source code or tested behaviour. "Documented" below means "the vendor says so", not "observed".
- Scope: the reference set already named in `REFERENCE_FEATURE_MATRIX.md` (Follow Up Boss, Pipedrive, HubSpot,
  Zoho CRM). No branding, copy or assets are reused; only requirement-relevant patterns are recorded.
- CrisGen UI mapping uses `crismag/development_design_systems` `crisgen-ui` 1.1 at e1c1a4f (the revision the
  app vendors). Gaps are flagged, not invented.

## 1. Findings by product

Each finding records source URL, retrieval date, edition/plan as documented, and access limits. "Page date"
is the vendor's own "last updated" line where one was shown; "not shown" means the page had none.

### Follow Up Boss (real-estate CRM)

| ID | Feature (documented) | What it does | AI or rules | Human control | Edition / limits | Source, page date |
|---|---|---|---|---|---|---|
| F-FUB-1 | Smart Summaries | Summarises calls and recaps a lead's whole history | AI (generative) | Not described | Marked beta. "No additional charge for AI", but relies on FUB Calling which is an add-on on some plans | [followupboss.com/features/ai](https://www.followupboss.com/features/ai), not shown |
| F-FUB-2 | Suggested Tasks | Proposes follow-up tasks; "activated with a single click" | AI | Suggest, user activates | As above | same page |
| F-FUB-3 | Smart Messages | Suggested texts/emails based on lead activity | AI (generative) | Draft offered to the user | As above | same page |
| F-FUB-4 | Predictive lead prioritisation | AI tags surfacing high-intent buyers/sellers (Zillow leads) | AI (predictive) | Automatic tagging | Tied to Zillow lead sources | same page |
| F-FUB-5 | Smart Actions (also titled "Automatic CRM updates", limited pilot) | Reads the call transcript after a call and proposes a stage change, follow-up appointment or timeframe change | AI | Stage/appointment: yes/no text to the agent, reminder after 2 h; timeframe changes applied automatically and logged. Admin can choose "suggest only" or "automatic" for early stages | Beta/pilot. Needs FUB Calling, call-recording power-up and Zillow two-way integration; Zillow buyer stages only | [Smart Actions](https://help.followupboss.com/hc/en-us/articles/37957434220055-Smart-Actions), not shown |
| F-FUB-6 | Data statement | Data "not used to train global AI models or any external systems"; AI "sees every call, text and email" in FUB | n/a | n/a | Vendor claim, unverified | features/ai page |
| F-FUB-7 | Automations (rule-based) | Stage-change and event triggered actions (already in matrix as Action Plans/Smart Lists) | Rules | Configured by admins | The "Automations 2.0 Overview" help article could not be retrieved (site returned an error on 2026-11-12) | [Automations 2.0](https://help.followupboss.com/hc/en-us/articles/33056241868311-Automations-2-0-Overview), not retrieved |

Takeaway: FUB's AI is concentrated on **calls and texts it carries itself**. The suggest-then-confirm pattern
(F-FUB-2, F-FUB-5) is the most transferable idea; the automatic-apply mode is not compatible with our audit
and ownership rules unless limited to non-ownership fields.

### Pipedrive

Source for all rows unless noted: [Pipedrive AI](https://support.pipedrive.com/en/article/pipedrive-ai),
page dated 3 September 2026. Plans named Lite, Growth, Premium, Ultimate.

| ID | Feature | What it does | AI or rules | Human control | Edition / limits |
|---|---|---|---|---|---|
| F-PD-1 | AI import assistant | Maps spreadsheet columns to CRM fields | AI | Not described | All plans; on by default |
| F-PD-2 | AI-assisted report creation | Builds an Insights report from a typed prompt | AI | User reviews the report | All plans |
| F-PD-3 | Sales Assistant (beta) | Chat that answers questions about deals/contacts/activities, summarises, drafts notes and emails | AI (OpenAI named as subprocessor) | User reads/asks; admin enables company-wide | Beta, "select group of users"; [article](https://support.pipedrive.com/en/article/sales-assistant), not shown. States customer data is not used to train models |
| F-PD-4 | AI email creation | Drafts an email from a short prompt, tone and length | AI (generative) | User reviews, then "Copy into message" and edits | Premium, Ultimate |
| F-PD-5 | AI-powered notifications | Context-based insights on company performance | AI | Informational | Premium, Ultimate; may not appear until several weeks of usage |
| F-PD-6 | Email summarisation (beta) | Thread summary, sentiment, buying readiness 1–10, action items | AI | User views output | Premium, Ultimate; beta enrolment |
| F-PD-7 | Suggested replies (beta) | Context-aware reply drafts for an email thread | AI | User chooses to use it | Premium, Ultimate; beta enrolment |
| F-PD-8 | Control model | Only account-settings admins enable AI; released vs beta features in separate settings | n/a | Admin switch per feature | All |

Takeaway: every generative feature is **opt-in at company level and produces a draft the user copies**. Data
retention and processing terms are not in the article (access limit: would need the privacy notice/DPA).

### HubSpot

| ID | Feature | What it does | AI or rules | Human control | Edition / limits | Source, page date |
|---|---|---|---|---|---|---|
| F-HS-1 | Record summary card | AI overview of a contact/company/deal/ticket: activities, notes, ownership; regenerates on open | AI (generative) | Read-only; "cannot be manually customized"; admins switch data sources and assistant access in AI settings; some activities excluded when Sensitive Data is on | All products and plans | [Summarize a record](https://knowledge.hubspot.com/records/summarize-records), 21 Sep 2026 |
| F-HS-2 | Deal scores | 0–100 win probability per open deal, top five +/− key factors, score history | AI (predictive) | "For information only"; factors shown | Sales Hub / Smart CRM Professional or Enterprise; factors need a Sales seat | [Use deal scores](https://knowledge.hubspot.com/records/use-deal-scores), 8 Dec 2025 |
| F-HS-3 | Predictive lead scoring | Likelihood a contact closes within 90 days + priority tier | AI (predictive, "blackbox") | No per-input explanation | Marketing or Sales Hub Enterprise | [Predictive lead scoring](https://knowledge.hubspot.com/properties/determine-likelihood-to-close-with-predictive-lead-scoring), 11 Jan 2026 |
| F-HS-4 | Lead scoring tool (rules) | Admin-defined points for properties and engagement | Rules (with AI insights add-on) | Admin-defined, inspectable | Not checked in detail | [Lead scoring overview](https://knowledge.hubspot.com/scoring/understand-the-lead-scoring-tool), not read in full |
| F-HS-5 | Agents (Agent Hub) | Data agent (enrichment), Prospecting agent (research + outreach), Deal progression recommendations, Customer agent (answers support chats), custom agents, agentic workflows | AI (agentic) | Admin activation; agents can be cloned/deleted; context/brand settings | Paid hubs, mostly Professional/Enterprise; consume HubSpot credits | [Agent Hub](https://knowledge.hubspot.com/ai/understand-breeze?facet1=crm), 26 Oct 2026 |

Takeaway: HubSpot pairs **explained scores** (deal scores show factors) with **unexplained ones** (predictive
lead scoring). Only the explained pattern fits our "attention must say why" rule (REQ-026).

### Zoho CRM (Zia)

| ID | Feature | What it does | AI or rules | Human control | Edition / limits | Source, page date |
|---|---|---|---|---|---|---|
| F-ZO-1 | Prediction / Zia scores | Lead and deal scoring, win/loss and delay prediction with recommended actions | AI (predictive) | Informational | Edition not stated on overview | [Zia overview](https://help.zoho.com/portal/en/kb/crm/zia/articles/zia-overview), not shown |
| F-ZO-2 | Anomaly detection | Flags unusual spikes/drops in tracked metrics; workflow anomalies over 7-day windows | Statistical | Alert | Not stated | same; [AI features overview](https://www.zoho.com/crm/ai-features-in-zoho-crm.html) |
| F-ZO-3 | Best time to contact | Suggests when to call/email from past response patterns; analytics on whether reps follow it | Statistical/AI | Suggestion | Enterprise and Ultimate with more than 20 user licences; needs email integration and telephony | [Best time to contact analytics](https://help.zoho.com/portal/en/kb/crm/zia-artificial-intelligence/communication/best-time-to-contact-customers/articles/zia-best-time-to-contact-analytics), not shown |
| F-ZO-4 | Email intent/sentiment/emotion; call transcription and sentiment | Classifies emails; alerts on consecutive negative emails; transcribes calls | AI | Alert | Call transcription has monthly minute caps (values not given) | overview pages |
| F-ZO-5 | Data enrichment | Adds demographic, social and firmographic data to records | AI + external data | "Manage enrichment usage" setting | Not stated | Zia overview |
| F-ZO-6 | Macro and workflow suggestions | Suggests automations from observed repetitive user actions | AI | Admin accepts | Not stated | Zia overview |
| F-ZO-7 | Generative (record summary, email drafting "Smart prompt", email/call summary) | LLM summaries and drafts | AI (generative) | Draft | Not stated | AI features overview |
| F-ZO-8 | Owner assignment suggestions (Zia Assignment) | Suggests record owner with per-user caps | AI | Suggestion; thresholds per user | Not stated | AI features overview |
| F-ZO-9 | Ask Zia | Natural-language questions, reminders, create tasks/meetings | AI | Conversational | Not stated | [Ask Zia](https://help.zoho.com/portal/en/kb/crm/zia-artificial-intelligence/conversational-ai/articles/ask-zia), not read in full |

Access limit: Zoho's edition-by-feature table ("Zia Ready Reckoner") is an embedded spreadsheet that could not
be read anonymously; edition claims above are only where a page stated them.

## 2. Cross-product patterns

1. **Summarise before you act** (F-FUB-1, F-HS-1, F-ZO-7, F-PD-6): a short generated recap of a record's
   history. Universally offered, low risk because it changes no data.
2. **Draft, never send** (F-FUB-3, F-PD-4, F-PD-7, F-ZO-7): AI produces a draft the person edits and sends.
3. **Suggest, then confirm** (F-FUB-2, F-FUB-5, F-ZO-6, F-ZO-8): structured suggestions (task, stage,
   owner) applied only on a click. FUB's optional auto-apply mode is the exception.
4. **Scores with reasons** (F-HS-2) versus **black-box scores** (F-HS-3, F-ZO-1, F-FUB-4).
5. **Anomaly and timing statistics** (F-ZO-2, F-ZO-3, F-PD-5) need weeks of data and integrated channels.
6. **Agents** that act on their own (F-HS-5 Customer/Prospecting agents) — the furthest from our rules.
7. **Admin opt-in per feature, data-use statements, credit/plan gating** everywhere.

Most valuable AI in the reference set depends on **channel data the vendor carries** (calls, texts, synced
email). Our CRM records interactions as typed summaries and has no telephony or inbound email sync (OQ-010),
so transcript-based features have no input here.

## 3. Constraints any candidate must respect

- ADR-001/ADR-002: no automation may change relationship ownership, accept a handover, or release to a pool.
  Suggestions may only *propose* these to the person entitled to act.
- REQ-026 / attention: derived at read time; a score or suggestion must state its reasons.
- Customer messages go through the sandbox transport and are labelled "not sent"; AI may draft, a person sends.
- Every applied suggestion writes an `audit(...)` row in the same `write_transaction` as the change.
- Worker jobs are idempotent and never hold a write transaction across slow work (an LLM call is slow work).
- No external enrichment of private individuals; no inferred sensitive traits (TARGET_USERS.md).
- Policy values via `get_policy()`; every AI item off by default and listed in `docs/IMPLEMENTATION_DEFAULTS.md`
  only if built.

## 4. Candidate automations

Tags: **R** = rule-based (deterministic, inspectable); **AI** = AI-assisted (model output, needs OQ-015).
Value/Effort: H/M/L, judgement only. Users: USER-001 agents, 002 sales/marketing, 003 commission-based,
004 management, 005 engagement/support. Plug-in points refer to the code on `main` at f59c420.

### Rule-based candidates (extend the existing deterministic engine)

| ID | Candidate | Reference pattern | Req / module | Users | Value | Effort | Data needed (exists?) | Risks | Plug-in point | CrisGen UI |
|---|---|---|---|---|---|---|---|---|---|---|
| C-R1 | **Explained priority score** in attention queue: points for open inquiry age, recent tour, open opportunity stage, agreed contact date, watchers | F-HS-2, F-HS-4 | REQ-016, REQ-026 / MOD-004 | 001, 003, 004 | H | M | Inquiry, Interaction, Opportunity, Watch (yes) | Weights are business choices; must stay a sort aid, not a ranking of people | `crm/attention/services.py` `evaluate()`/`AttentionItem.severity`; weights in `crm/core/policy.py` | Chip (score + reasons), Table, details disclosure for "why" (gap: Tooltip needs JS) |
| C-R2 | **Stalled opportunity** reason: no stage change or interaction in N days, or `expected_close` passed | F-HS-2 (stalling factor), F-ZO-1 | REQ-022, REQ-026 / MOD-007, MOD-004 | 001, 003, 004 | H | L | Opportunity stage history (audit rows only; no stage-change timestamp field) | False alarms on long sales cycles | New `Reason` in `crm/attention/services.py`; rule row in `crm/automation/catalog.py` | Chip (warning), existing attention queue |
| C-R3 | **Suggested follow-up task after an interaction** (e.g. tour logged → "follow up in 2 days" pre-filled) | F-FUB-2 (rule-based variant) | REQ-016, REQ-020 / MOD-002, MOD-003 | 001, 003, 005 | H | L | Interaction kind (yes) | Pre-filled forms must not auto-create tasks | `crm/contacts/views.py` add_interaction redirect → task form defaults; policy map kind→offset | Alert (suggestion) + Button "Create task", Input/Select |
| C-R4 | **Routing suggestion for pool coordinators**: least-loaded or round-robin candidate shown when reviewing pool clients | F-ZO-8, Zoho assignment rules (matrix) | REQ-014, ADR-002 / MOD-002 | 004 | M | M | Open task counts, active relationships per person (yes) | Must stay a suggestion; manual claim stays the rule | `crm/work/services.py` + Shared work view | Table, Chip, Button "Offer to …" |
| C-R5 | **Source volume anomaly** in reports: inquiries/acquisitions per source vs trailing average | F-ZO-2, F-PD-5 | REQ-017, REQ-022 / MOD-007 | 002, 004 | M | M | Source, Inquiry, Contact.created_at (yes); needs weeks of history | Small numbers produce noisy alerts; unavailable ≠ zero | `crm/reporting/metrics.py`; optional `digest` content | Card stat tile, Chip (up/down), Alert |
| C-R6 | **Better duplicate matching** at capture/intake (name similarity, phone variants) | F-PD-1 (import), F-ZO-5 | REQ-003–006 / MOD-001 | 001, 002, 005 | M | L | Contact fields (yes) | Wrong merges; keep "suggest, never merge" | `crm/contacts/services.py` `duplicate_candidates()` | Alert (candidates), List, Button |
| C-R7 | **Contact-time hint** from own logged outcomes (hour/day when past contacts succeeded) | F-ZO-3 | REQ-020 / MOD-003 | 001, 003 | L | L | Interaction kinds `outbound_attempt` vs `conversation` with `occurred_at` (yes) | Needs months of volume per contact before useful; timezone of the customer unknown | Derived read in `crm/contacts/views.py` contact_detail (no new field) | Chip, facts list |

### AI-assisted candidates (proposals, need OQ-015)

Common design if any is promoted: a new `crm/assist/` app with a provider interface (no vendor chosen), a
`Suggestion` record (target, kind, payload, status proposed/accepted/dismissed, model id, input hash,
created/decided by/at), generation in a worker job outside any write transaction, accept/dismiss through a
service that writes the domain change and `audit(...)` together, a per-feature policy switch defaulting to off,
and a visible "AI-generated, check before use" label. No suggestion is ever applied without a person.

| ID | Candidate | Reference pattern | Req / module | Users | Value | Effort | Data needed (exists?) | Risks | Plug-in point | CrisGen UI |
|---|---|---|---|---|---|---|---|---|---|---|
| C-A1 | **Relationship summary** on the contact profile and in handover requests | F-HS-1, F-FUB-1, F-ZO-7, F-PD-3 | REQ-015, REQ-016 / MOD-003, MOD-002 | All five | H | M | Interaction.summary, Inquiry.message, notes, tasks, opportunities (yes) | Hallucinated facts; personal data sent to a provider; stale summaries | Profile view `crm/contacts/views.py` contact_detail; handover form `crm/work/views.py` handover_new | Card + Typography, Alert (info) "AI summary, check the history", Button "Regenerate" |
| C-A2 | **Follow-up draft** for a customer email from a chosen template and recent history | F-FUB-3, F-PD-4, F-PD-7, F-ZO-7 | REQ-020, REQ-023 / MOD-006 | 001, 003, 005 | H | M | Templates, history (yes); opt-out flag (yes) | Tone/accuracy, claims about properties or prices; must keep sandbox "not sent" labelling | `crm/comms/services.py` (draft only, then existing `schedule_customer_message`) | Textarea (editable draft), Alert "Draft, not sent", Button |
| C-A3 | **Inquiry triage**: extract budget, area, timeframe, intent and urgency from inquiry text into suggested fields | F-ZO-4, F-PD-6 | REQ-003–006, REQ-019 / MOD-001 | 002, 005, 001 | M | M | Inquiry.message (yes); structured fields for budget/area (**partly missing**: only free-text `interests`) | Wrong extraction; inferring sensitive traits must be blocked | `crm/contacts/intake.py` and `record_inquiry` → Suggestion | Chip per suggested field, Button "Apply" |
| C-A4 | **Next-action suggestion from interaction notes** (task + due date proposed after logging a call/tour) | F-FUB-5, F-FUB-2 | REQ-016, REQ-020 / MOD-002, MOD-003 | 001, 003, 005 | H | M | Interaction.summary (yes) | Never changes lifecycle/ownership; only proposes a task | after `record_interaction` → worker job → Suggestion shown on profile/Today | List, Button "Create task"/"Dismiss" |
| C-A5 | **Manager digest narrative**: a few sentences on what changed in team attention this week | F-PD-5 | REQ-017, REQ-026 / MOD-004 | 004 | M | L | Attention items, digest counts (yes) | Summary may hide items; counts must stay authoritative | `crm/automation/engine.py` `run_digest` | Card, List, Chip |
| C-A6 | **Plain-language report question** ("toured but no offer in October by source") turned into existing filters | F-PD-2, F-ZO-9 | REQ-022 / MOD-007 | 002, 004 | M | H | Report filters (yes) | Wrong filter silently; must show the resulting filter for review | `crm/reporting/views.py` → existing filter params only | Input, Chip (applied filters), Table |
| C-A7 | **Reply sentiment / readiness flag** on customer replies | F-PD-6, F-ZO-4 | REQ-020 / MOD-006 | 001, 005 | L | M | Inbound replies (**missing**: no email sync, OQ-010) | Blocked on integration | `on_customer_replied` in `crm/automation/engine.py` | Chip |
| C-A8 | **Predictive conversion score** (trained model) | F-HS-3, F-ZO-1, F-FUB-4 | REQ-016 / MOD-004 | 004, 002 | L | H | Hundreds of closed outcomes (**missing** at this scale) | Unexplainable; bias; conflicts with REQ-026 reasons | — (recommend not pursuing; C-R1 covers the need) | Progress bar (gap: needs inline width, blocked by CSP) |

### Not recommended

| Pattern | Why not |
|---|---|
| Call transcription and call summaries (F-FUB-1/5, F-ZO-4) | No telephony in scope; recording consent obligations |
| Auto-apply stage or owner changes (F-FUB-5 automatic mode, F-ZO-8 auto) | Conflicts with ADR-001/002 and audit expectations |
| External data enrichment of people (F-ZO-5, HubSpot Data agent) | Private individuals' data; no lawful-basis decision |
| Autonomous customer-facing agents (HubSpot Customer/Prospecting agents) | Customer messaging must be human-sent; out of first-release scope |

## 5. CrisGen UI 1.1 gaps raised by these candidates

| Need | Status in CrisGen 1.1 | Suggested handling |
|---|---|---|
| "AI-generated" marker | No dedicated component | `Chip` `data-color="info"` with text label; propose an upstream `Provenance`/label variant |
| Reason tooltip on a score | `Tooltip`/`Popover` exist but need JavaScript; the app ships none (strict CSP) | Native `<details>` as today, or add a CSP-compatible script |
| Score bar | `Progress` examples set width with inline `style`, which the CSP forbids | Show the number in a `Chip`; or upstream a `data-value`/class-based Progress |
| Suggestion card (accept/dismiss) | Compose from `Card` + `Alert` + `Button`; no dedicated pattern | Propose a "suggestion" pattern upstream |
| Stat with trend (C-R5) | Already a known gap (`Stat`) in `docs/UI_COMPONENTS.md` | Reuse current `.stat` layout |

## 6. Recommended order if Cris promotes items

1. Rule-based, no new data: C-R2, C-R3, C-R6, then C-R1 (needs agreed weights).
2. First AI pilot, read-only and lowest risk: C-A1 relationship summary, behind a policy switch, demo data only.
3. Then C-A4 and C-A2, both suggest/draft-only.
4. Revisit C-R5, C-A3, C-A5, C-A6 after real usage data; C-A7 after OQ-010; drop C-A8.

## 7. Open questions for OQ-015

- Which candidates to promote, defer or reject.
- Whether any customer or contact data may be sent to an external AI provider, and under what terms
  (retention, training, region). Until answered, AI features may run only on demo data.
- Whether a self-hosted model is required.
- Who may switch AI features on (workspace admins only is the proposed default, mirroring F-PD-8).
