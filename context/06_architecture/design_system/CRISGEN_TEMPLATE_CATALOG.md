# Inspected template/composition catalog
Revision e1c1a4f1e98ecc4dec9ae4eb16fa646069e94278, subdirectory crisgen-ui. Partial source inspection, not runtime testing.
| Source-qualified key | Evidence | Verified structure | Proposed CRM use / limits |
|---|---|---|---|
| CrisGen/dashboard-shell | patterns/dashboard-shell/spec.json and README.md | Regions sidebar, navbar, content; sidebar hidden below bp-lg; content table scrolls internally | Shared internal shell; mobile navigation must be implemented/verified, not assumed |
| CrisGen/data-table | patterns/data-table/spec.json and README.md | Header/actions; optional filters/search; table; pagination. Regions /children/0,2,4,6 | Contacts, pools, attention lists; source placeholder copy is not CRM content |

README documents renderInstance/PATTERNS approach for React and composing from spec trees; selected target implementation/exported symbols were not inspected. Do not issue executable imports from this catalog. Dashboard shell is a CrisGen-designed template; data-table is source-derived. Their source classification does not validate application behavior.
Other llms-indexed templates are candidates only, omitted until individually inspected.
