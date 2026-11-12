# Reference feature matrix
Revision 24. Based on official documentation previously researched in this project; not newly inspected signed-in UI. Verify current feature editions and behavior during TASK-002.
| Product/source | Observed documented pattern | CRM adaptation | Limitation |
|---|---|---|---|
| [Follow Up Boss pools](https://help.followupboss.com/hc/en-us/articles/4422920700439-Lead-Ponds-Moving-Leads-to-a-Pond) | Pooled leads, claim/release timeline and notification consequences | Shared client queue, explicit responsibility | Our coordinator-acceptance policy is our own approved rule |
| [Smart Lists](https://help.followupboss.com/hc/en-us/articles/360034301034-Working-Your-Smart-Lists) | Saved filters using stage and last communication | Attention lists and forgotten-client resurfacing | Need actual CRM activity definitions |
| [Action Plans](https://help.followupboss.com/hc/en-us/articles/1500008539982-Action-Plans-Overview) | Follow-up emails and tasks | Bounded sequences with stop conditions | Do not import vendor sender/permission defaults |
| [Pipedrive Leads Inbox](https://support.pipedrive.com/en/article/leads-inbox) | Lead organization before pipeline deal | Focused intake/work queue | Our lifecycle definitions remain proposed |
| [Pipedrive activities](https://support.pipedrive.com/en/article/activities) | Activities tied to sales work | Next actions visible in daily workspace | No proof of actual engagement from task count alone |
| [HubSpot sales](https://www.hubspot.com/products/sales) | Contact/lead management, sequences and reporting | Shared history and follow-up rules | No AI features needed for baseline |
| [HubSpot attribution](https://knowledge.hubspot.com/reports/understand-attribution-reporting) | Marketing contribution to contacts/deals/revenue | Source-to-outcome reporting | Instrumentation and financial data unresolved |
| [Zoho assignment](https://help.zoho.com/portal/en/kb/crm/automate-business-processes/assignment-rules/articles/set-assignment-rules) | Rules and round-robin assignment | Configurable routing later | Manual claiming adopted initially |
| [Zoho Blueprint](https://help.zoho.com/portal/en/kb/crm/faqs/blueprint/articles/faqs-blueprint) | Process states/transitions | Explicit handovers and stage rules | Not a mandate to build full visual process designer |
| [Follow Up Boss AI](https://www.followupboss.com/features/ai) (beta; retrieved 2026-11-12) | Smart Summaries, Suggested Tasks, Smart Messages, AI lead tags | AI candidates C-A1, C-A2, C-A4 (proposal, OQ-015) | Vendor page only; most inputs are FUB-carried calls/texts we do not have |
| [FUB Smart Actions](https://help.followupboss.com/hc/en-us/articles/37957434220055-Smart-Actions) (beta/pilot) | Transcript-based stage/appointment suggestions confirmed by yes/no; optional auto-apply | Suggest-then-confirm only (C-A4) | Auto-apply conflicts with ADR-001/002; needs telephony |
| [Pipedrive AI](https://support.pipedrive.com/en/article/pipedrive-ai) (page 3 Sep 2026) | Admin opt-in AI: email drafts, thread summary/readiness, suggested replies, report from prompt, import mapping | C-A2, C-A6, C-R6; admin-only switch | Premium/Ultimate for most; processing terms not in article |
| [HubSpot record summary](https://knowledge.hubspot.com/records/summarize-records) (21 Sep 2026) | Read-only AI recap of a record | C-A1 | Cannot be edited; sensitive-data exclusions |
| [HubSpot deal scores](https://knowledge.hubspot.com/records/use-deal-scores) (8 Dec 2025) | Win probability with top +/− factors | Explained rule-based score C-R1, stalled reason C-R2 | Pro/Enterprise; we prefer deterministic reasons (REQ-026) |
| [HubSpot predictive lead scoring](https://knowledge.hubspot.com/properties/determine-likelihood-to-close-with-predictive-lead-scoring) (11 Jan 2026) | Black-box 90-day close likelihood | Not recommended (C-A8) | Enterprise; unexplainable; needs volume |
| [HubSpot Agent Hub](https://knowledge.hubspot.com/ai/understand-breeze?facet1=crm) (26 Oct 2026) | Data, prospecting, deal-progression and customer agents | Not recommended for first release | Credits; autonomous customer contact |
| [Zoho Zia](https://help.zoho.com/portal/en/kb/crm/zia/articles/zia-overview) | Scores, anomaly detection, best time to contact, sentiment, enrichment, workflow/owner suggestions, generative summaries | C-R4, C-R5, C-R7, C-A3 | Edition table not readable anonymously; best-time needs Enterprise+ and >20 users |

AI/automation rows above added 2026-11-12; details, editions and access limits in AI_AUTOMATION_RESEARCH.md. All AI items are proposals pending OQ-015.

Research record must distinguish source documentation, source code, screenshot observation and actual tested behavior. No copied branding/assets or claim of equivalent implementation. UI research task records URL/date/edition/access limits and only requirement-relevant patterns.
