# Known limitations and backlog

This build is a complete, locally runnable CRM with automated evidence. It is **not production-ready**
until the items marked *Before pilot* are done and the product owner has reviewed the
[implementation defaults](IMPLEMENTATION_DEFAULTS.md).

## Before pilot

| Item | Why | Notes |
|---|---|---|
| Owner review of implementation defaults | Every timing, cadence, lifecycle and email rule is an engineer's default, not an approval | OQ-002, OQ-008, OQ-010, OQ-011, OQ-012 |
| Hosting decision and TLS | Production settings exist but no server was set up | OQ-012; see OPERATIONS.md |
| Disk encryption + backup destination + restore drill | SQLite and backups are unencrypted | OPERATIONS.md |
| Real email provider (if customer email is wanted) | Only the sandbox transport exists | Needs provider choice, sender identity, SPF/DKIM, signed callbacks, bounce handling, sandbox-account test |
| Usability pass with 2–3 agents and a coordinator | No user has tried the screens | Watch capture, claim, handover and attention flows |
| Accessibility review | Semantic HTML, labels, keyboard-reachable native controls and focus styles are in place; no audit with assistive tech was done | WCAG 2.1 AA check |

## Product backlog (not in this build)

- Customer email replies are not ingested; staff log "inbound reply" interactions manually.
- Earnings / recognised revenue / commissions (OQ-011; payout accounting is out of scope).
- Engagement metrics beyond logged interactions (no website/email tracking).
- Saved dynamic filters for watchlists (recommended, not required by REQ-021).
- Sales pipeline board view (stages are a table column today).
- Bulk reassign. (CSV import exists since 2026-11-13.)
- Data retention and deletion workflow (only archiving).
- SSO (password reset by email and two-step sign-in exist since 2026-11-13).
- Notification channels other than in-app (email/SMS/chat to staff).
- Attention digest delivered by email (today it is an in-app notification).
- Calendar for tours/viewings (tours are logged as interactions; future ones as tasks).
- Multi-language UI.
- Small JavaScript layer for CrisGen Drawer/Modal/Tabs (blocked today by "no JavaScript" choice, not by CSP).

## Technical limits

- One worker process and one web process are the tested configuration (SQLite single writer).
- The worker polls every 5 s; reminders are minute-accurate, not second-accurate.
- The attention queue is computed on request over all active contacts; fine for thousands of contacts,
  should be measured before tens of thousands.
- MySQL is documented, not tested.
- Timezone is per workspace, not per user.
