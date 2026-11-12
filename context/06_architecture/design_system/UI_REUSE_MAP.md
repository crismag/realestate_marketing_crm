# Proposed UI reuse map
Model 23. Source revision is in DESIGN_SOURCE.yaml. Verified source structure does not mean selected CRM composition is approved or tested.
| Section / module | Users / requirements | Inspected candidate | Adaptation and checkpoint | Remaining evidence |
|---|---|---|---|---|
| Internal shell | All users; REQ-002 | CrisGen/dashboard-shell | CRM destinations and context; mobile navigation/keyboard | Target implementation, theme and navigation behavior |
| Contacts MOD-001 | USER-001,002,005; FR-001 | CrisGen/data-table | CRM search/filter/actions and linked profile | Input/table/button types and app query contract |
| Shared pools MOD-002 | USER-001,003,004; REQ-014,015 | CrisGen/data-table | Claim/accept actions, pending status; ICP-001,002 | Actual action API and variants |
| Today MOD-004 | All users; REQ-026 | CrisGen/dashboard-shell + data-table | Attention reasons/counts; ICP-003,005 | Queue contract, responsive composition |
| Interaction history MOD-003 | All users; REQ-016,026 | CrisGen/Timeline README | Recorded evidence and timestamps, semantic ordered history | Spec/examples/target/API |
| Sales, Marketing, Automation, Configuration | Relevant matrix rows | No selected inspected template | Research needed | Do not invent board/chart/rule-builder component |

Tokens/themes: README documents CrisGen Light/Dark and semantic tokens; actual contrast/focus in consuming app must be tested. Inspect selected token/theme files before using exact values. Hook locations, task IDs and component bindings remain unresolved because no app code exists.
