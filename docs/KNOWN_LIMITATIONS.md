# Known limitations and backlog

This build is a complete, locally runnable CRM with automated evidence. It is **not production-ready**
until the items marked *Before pilot* are done and the product owner has reviewed the
[implementation defaults](IMPLEMENTATION_DEFAULTS.md).

## Before pilot

| Item | Why | Notes |
|---|---|---|
| Owner review of implementation defaults | Every timing, cadence, lifecycle and email rule is an engineer's default, not an approval | OQ-002, OQ-008, OQ-010, OQ-011, OQ-012 |
| Hosting decision and TLS | A Docker kit with automatic HTTPS exists (`deploy/`, tested locally on 2026-11-13); no real server was set up | OQ-012; see INSTALL_NEW_COMPANY.md |
| Backup destination + restore drill | Backups are encrypted when `CRM_BACKUP_KEY` is set; copying them off the server and a drill per install are still manual | INSTALL_NEW_COMPANY.md |
| Real email provider (if customer email is wanted) | Only the sandbox transport exists | Needs provider choice, sender identity, SPF/DKIM, signed callbacks, bounce handling, sandbox-account test |
| Usability pass with 2–3 agents and a coordinator | Only an automated walk-through of every screen was done | Use docs/PILOT_TEST_SCRIPT.md |
| Accessibility review | Semantic HTML, labels, keyboard-reachable native controls and focus styles are in place; no audit with assistive tech was done | WCAG 2.1 AA check |

## Product backlog (not in this build)

- Customer email replies are not ingested; staff log "inbound reply" interactions manually.
- Earnings / recognised revenue / commissions (OQ-011; payout accounting is out of scope).
- Engagement metrics beyond logged interactions (no website/email tracking).
- Saved dynamic filters for watchlists (recommended, not required by REQ-021).
- Sales pipeline drag-and-drop. The board is columns plus an explicit "Move stage" dialog (a stage change is a saved POST).
- Bulk reassign. (CSV import exists since 2026-11-13.)
- Data retention and deletion workflow (only archiving).
- SSO (password reset by email and two-step sign-in exist since 2026-11-13).
- Notification channels other than in-app, except the daily digest's staff-mail copy (file folder, or SMTP when `CRM_STAFF_SMTP_HOST` is set). SMS and chat are still absent.
- The digest staff copy is not a customer message and is not a general staff email channel.
- Calendar for tours/viewings (tours are logged as interactions; future ones as tasks).
- Multi-language UI.
- CrisGen behaviours other than Drawer, Modal and Tabs (those three are in `static/crm/behaviors.js`). Dropdown, popover, tooltip, select listbox, accordion and collapse are not loaded.

## Technical limits

- One worker process and one web process are the tested configuration (SQLite single writer).
- The worker polls every 5 s; reminders are minute-accurate, not second-accurate.
- The attention queue is computed on request over all active contacts; fine for thousands of contacts,
  should be measured before tens of thousands.
- MySQL is documented, not tested.
- Timezone is per workspace, not per user.

## Hardening follow-up (13 November 2026)

- Inbound reply response matching uses contact-level chronological human-response evidence, not a reply-thread identifier. Staff must still log responses accurately.
- Daily digest change counts compare with the previous delivered digest snapshot, not every transient state between digests. Reassignment can count as resolved for the old handler.
- Run normal migrations before starting the upgraded web/worker. `automation.0003_digest_snapshots` adds the comparison baseline, and `automation.0004_digest_staff_email` records whether the staff copy was filed. The first post-upgrade digest establishes the baseline. Older digests stay in-app only.
- Local environment cannot launch Chromium (socket permission denied), but fresh desktop/390px browser verification passed in GitHub Actions run 43345965197 at bd49e60. See current run report for exact checks.
