# Implementation defaults

These choices were made by the implementing engineer so the CRM could be built and tested end to end.
**None of them is a business approval.** Each is configurable (under **Settings** unless noted) and each
maps to an open decision in [`context/04_requirements/OPEN_DECISIONS.md`](../context/04_requirements/OPEN_DECISIONS.md)
that the product owner still owns.

Approved rules that the build enforces as written (not defaults):

- **ADR-001**: the sender stays responsible until the recipient accepts a handover.
- **ADR-002**: claims from a shared pool are atomic and exclusive; releasing a client to a pool needs the
  pool coordinator's acceptance; overdue work never removes ownership automatically.
- One shared workspace; every signed-in colleague can see and work on every customer. "Administrator" only
  adds settings and user management. No customer portal, tenancy, payout accounting or property inventory.

## Technical defaults (owner decision OQ-012)

| Topic | Default | Where to change |
|---|---|---|
| Stack | Python 3.13, Django 5.2 LTS, server-rendered pages, SQLite in WAL mode | Code; MySQL path in [MYSQL_MIGRATION.md](MYSQL_MIGRATION.md) |
| Hosting | One web process (waitress, threaded) + one worker process behind a TLS proxy | [OPERATIONS.md](OPERATIONS.md) |
| Authentication | Email + password (Argon2), 12 h sessions, lockout after 5 failures in 15 min | `CRM_SESSION_HOURS`, `CRM_LOGIN_MAX_FAILURES`, `CRM_LOGIN_LOCK_MINUTES` |
| Timezone / currency | Asia/Shanghai, USD (storage is UTC; money in integer minor units) | Settings |
| Customer email | Local sandbox transport only; nothing is sent | `CRM_EMAIL_TRANSPORT` (only `sandbox` exists) |
| Backups | Manual/cron `backup_db`; unencrypted files with 0600 permissions | [OPERATIONS.md](OPERATIONS.md) |

## Product defaults

| Decision | Default | Open decision |
|---|---|---|
| Lifecycle | One contact record: lead → prospect → client. A contact becomes a client when one of its opportunities is **won** | OQ-002 / PROP-032 |
| Sales stages | new, qualification, viewing, proposal, decision; won/lost are outcomes, not stages | Settings (labels and stages) |
| Duplicate matching (C-R6) | Normalised email, also ignoring a "+tag" (jane+web@ = jane@); normalised phone (≥7 digits); exact name, or the same name ignoring case, accents, punctuation and word order when it has two or more words. The capture screen says which of these matched. Never merged automatically; the user confirms "different person". The wider checks can be switched off in Settings (exact email/phone/name remain) | Settings, TASK-004 open issue, OQ-015 |
| Web intake identity | Exact email match to exactly one active contact reuses it; otherwise a new contact in the intake pool, other candidates flagged in the audit log | OQ-010 |
| What counts as contact | Outbound attempt, conversation, inbound reply, tour. Notes and profile views never count | Settings |
| After a tour | Flag if no follow-up task or contact within 48 h | Settings |
| Stalled opportunity (C-R2) | Flag an open opportunity whose stage has not changed for 21 days (0 = off), or that is still open after its expected close date (on/off). Only a real stage change resets the clock; editing title or amount does not. Deals that existed before the upgrade start their clock at the upgrade (no history to go on). One reason per contact lists every stalled deal; snoozable | Settings, OQ-015 |
| Follow-up suggestion (C-R3) | After you log an interaction, the next-action form is pre-filled (never created): tour → "Follow up after the tour" in 24 h; conversation → 72 h; no-answer attempt → try again in 24 h; customer reply → respond in 4 h; notes → nothing. Skipped when the contact already has a future task. On/off in Settings; titles and hours in the stored policy (`followup_suggestions.by_kind`) | Settings, OQ-015 |
| Inactivity cadence | Lead 7 days, prospect 14, client 60 (0 = off) | Settings, OQ-008 |
| Inquiry response target | 24 h | Settings |
| Pool waiting / pending handover reminders | 24 h each | Settings |
| Overdue escalation | Tasks overdue by 72 h notify the configured escalation recipients; with nobody configured a visible "routing gap" is recorded | Settings |
| Snoozing | Allowed for after-tour, inactivity, missing next action, stalled opportunity and pool waiting, with a reason and end date. Never for unanswered inquiries, overdue tasks, promises or critical tasks | Code (`crm/attention/services.py`) |
| Daily digest | 08:00 workspace time, in-app | Settings, Automation |
| Attention sweep | Every 15 minutes; missed runs coalesce into one | Settings |
| Customer email rules | Inquiry acknowledgement and client onboarding, both enabled, sandbox only | Automation (enable/disable, versioned) |
| Customer quiet hours | 20:00–08:00 workspace time; sends are deferred | Settings |
| Frequency cap | At most one automated email per customer per 72 h | Settings |
| Stop policies | Opt-out, archived, no email, inquiry already answered, customer replied, rule disabled (queued messages cancelled), template inactive | Code (`crm/comms/services.py`) |
| Uncertain delivery | Never retried automatically (avoids double sends); a person records the outcome | Code |
| Provider failure | Retried with backoff (4 attempts in total), then shown as failed; a person can retry, which re-checks every stop policy | Code |
| Reports | Definitions v`2026-11-13.1` in `crm/reporting/metrics.py`; spend counts only entries wholly inside the period (not prorated); earnings unavailable | OQ-011 |
| Criticality | A task can be flagged critical; it always surfaces in attention | REQ-017 open issue |
| Notifications | In-app only; reading or dismissing never completes the underlying work | REQ-019 |
| Deactivated colleague | Their clients show as "Responsible colleague deactivated" in every administrator's attention queue; an administrator may request the handover on their behalf; the recipient must still accept | Code (`crm/work/services.py`) |
| Source codes | Derived from the label when left empty | Code (`crm/core/settings_forms.py`) |
| Company profile | Name, registered name, phone, email, website, address on *Settings → Company profile*; versioned with the other settings; usable in customer emails as `{{ company_phone }}`, `{{ company_email }}`, `{{ company_website }}`, `{{ company_address }}` | Settings |
| Logo | PNG, JPEG or WebP up to 512 KB, stored in the database (so backups include it), served publicly at `/brand/logo` for the sign-in page; SVG refused | Code (`crm/core/settings_forms.py`) |
| First-run checklist | Administrators see "Set up your CRM" on Today until company profile, settings review, people, a pool with a coordinator and a first contact exist | Code (`crm/core/views.py` `setup_steps`) |
