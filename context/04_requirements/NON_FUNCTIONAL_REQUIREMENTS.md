# Non-functional requirement register
Revision 24. Existing NFR-001–004 remain proposed; do not invent numeric targets.
| Existing ID / topic | Expected outcome | Evidence / open value |
|---|---|---|
| NFR-001 authentication | Anonymous internal read/write denied server-side | Actual identity/session mechanism unknown |
| NFR-002 traceability | Important changes identify actor/rule/time without secrets | Retention and immutability scope unresolved |
| NFR-003 scheduled action reliability | Restart preserves due work; replay avoids duplicate logical action | Delivery SLO/recovery horizon unknown |
| NFR-004 interface states | Distinguish loading, empty, invalid, conflict and failure | Devices/accessibility targets unknown |

Proposed quality topics requiring a decision: latency/concurrency/data volume; uptime/recovery; backup restore tests; secret management; retention/deletion; localization/currency/timezone; export/import; accessibility/keyboard; deployment portability; operational ownership. These are knowledge gaps, not accepted service levels.
Do not choose architecture by assuming enterprise-scale concurrency, offline support or strict multi-region availability. Record a measurable target and owner before claiming compliance.
