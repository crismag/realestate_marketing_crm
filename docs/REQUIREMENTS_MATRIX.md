# Requirement → implementation → evidence

Historical baseline evidence below was produced on branch `claude/project-thread-2p04se` in the build container
(Python 3.13.18, Django 5.2.19, SQLite 3.53, Chromium via Playwright 1.63). "Passed" means the named check
ran and passed there; it is re-run by CI on every push. Nothing here has been verified with real users,
real customer data or a real email provider.

Commands: `pytest -p no:logging` (all `tests/`), `scripts/e2e.sh` (production-like server + browser).

## Delivery stages

| Stage | Scope | Status | Evidence |
|---|---|---|---|
| A | Defaults and contracts | Done | [IMPLEMENTATION_DEFAULTS.md](IMPLEMENTATION_DEFAULTS.md), `crm/core/policy.py` |
| B | Foundation, SQLite, auth, tooling | Done | `test_fresh_database_migrates_from_zero`, auth tests in `tests/test_web.py`, CI workflow |
| C | Capture, search, relationships | Done | `tests/test_capture_reporting.py` (AT-006), e2e steps 1–3 |
| D | Responsibility, claims, handovers, pools | Done | `tests/test_responsibility.py`, `tests/test_concurrency.py`, e2e steps 2, 7, 8 |
| E | Interactions, tours, tasks, next actions | Done | `tests/test_responsibility.py` (tasks), `test_future_interaction_rejected_and_recording_time_kept`, e2e 3–4 |
| F | Attention queue | Done | `tests/test_attention.py`, e2e 5 |
| G | Durable automation, reminders, notifications | Done | `tests/test_automation.py`, e2e 6 |
| H | Communications sandbox, templates, providers | Done for sandbox; **no real provider** | `tests/test_automation.py` (stop policies, timeout, failure), Messages screen |
| I | Reporting | Done for declared metrics; earnings unavailable by design (OQ-011) | `test_report_counts_reconcile…`, `test_report_page_shows_not_applicable…`, e2e 9 |
| J | Acceptance, security, recovery, handoff | Done locally; pilot acceptance not run | This file, [SECURITY.md](SECURITY.md), `tests/test_operations.py` |

## Requirements

| ID | Requirement (short) | Implementation | Evidence | Status / notes |
|---|---|---|---|---|
| REQ-001/002 | All signed-in staff can use all functional areas; filters, not hidden permissions | No per-record permissions; "Administrator" only for settings/users | `test_every_page_renders_for_admin_with_data`, `test_non_admin_cannot_manage_users_or_settings` | Met |
| REQ-003–006 | Capture from walk-in, referral, website, roadshow; invalid input kept; duplicates surfaced, never auto-merged; intake reports success only after persistence | `crm/contacts` capture form, sources, `intake.py` API | AT-006 tests, `tests/test_intake.py` | Met. Customer login (REQ-006 part) deferred by scope |
| REQ-003–006 (C-R6) | Duplicate candidates also match +tag email variants and the same multi-word name in any order/without accents; each candidate shows why it matched | `crm/contacts/services.py` `duplicate_candidates`, `match_reasons`, `Contact.name_key` | `tests/test_rule_automations.py` | Met as implementation default |
| FR-001 | Search and linked history | Contacts list search/filters, profile timeline | `test_empty_and_filter_empty_states_are_distinct`, e2e | Met |
| REQ-014 | Individual vs pool handling; visible responsibility and history; exclusive claims | `crm/work` Assignment, AssignmentEvent, `claim()` | AT-001: `test_simultaneous_claims_have_exactly_one_winner`, `test_claim_*` | Met (ADR-002) |
| REQ-015 | Tasks to others without ownership transfer; handovers with context; failed transfer keeps history | `request/accept/decline/cancel_handover`, task dispositions | AT-002 tests in `test_responsibility.py`, `test_simultaneous_accepts…` | Met (ADR-001) |
| REQ-014/015 (pilot finding) | A deactivated colleague's clients do not get stuck: they surface in attention for administrators, and an administrator may start the handover; the client stays with the deactivated colleague until the recipient accepts (ADR-001) | `crm/work/services.py` `can_initiate_handover`, `handler_inactive` reason in `crm/attention/services.py`, warning in `crm/accounts/views.py` `user_edit` | `tests/test_departed_colleague.py` | Met as implementation default |
| REQ-016 | Show responsibility, last activity, next action; find unattended; explain alerts; profile view is not contact | `crm/attention` evaluation with reasons and facts | AT-003: `test_toured_client_without_task…`, `test_profile_view_and_notes_do_not_count_as_contact` | Met |
| REQ-017 | Supervisory view by person/team/period with drill-down; critical work | Attention filters (person/team/pool/reason), Reports by person, critical tasks | `tests/test_attention.py`, report tests | Met; criticality levels beyond a flag are open |
| REQ-018 | Onboarding emails: correct event, visible failures, no duplicates | `onboard` rule on opportunity won, sandbox transport | `test_inquiry_ack_is_sandbox_captured…`, `test_replayed_intake_event_does_not_duplicate_message` | Met in sandbox; event choice is a default (OQ-008) |
| REQ-019 | Notify handler/watchers; link and reason; read ≠ done | `Notification` with reason/links; read/dismiss separate | `test_new_inquiry_notifies_current_handler_once`, `test_pool_inquiry_routes_to_coordinator…` | Met in-app. The daily digest can also prepare a staff-only copy (`tests/test_staff_digest.py`); that copy is not a customer message. Other notifications stay in-app |
| REQ-020 | Reminders with due times; inactivity reset types shown; recheck before execution; no duplicate retries | Tasks, sweep rules, stop policies, logical keys | `test_sweep_is_idempotent_and_reassignment_reroutes`, `test_customer_reply_before_send…`, `test_opt_out…`, `test_quiet_hours…` | Met |
| REQ-021 | Watchlists; stop watching; no ownership change | `Watch`, watch rule | `test_watch_then_unwatch`, `test_watch_does_not_change_ownership` | Met |
| REQ-022 | Reports with period, definitions, reconciliation, unknown ≠ zero | `crm/reporting/metrics.py`, drill-downs, spend | AT-005 tests | Met for acquisitions, inquiries, won count/value, spend, CPA, response time, activity. Earnings unavailable (OQ-011) |
| REQ-022 (sales board) | Opportunity list and board; explicit stage move | `crm/contacts/views.py` `opportunities` / `opportunity_stage`, `move_opportunity_stage` | `tests/test_sales_board.py`; e2e filter drawer, list/board tabs, stage move; 390px board | Met as implementation default. Moving a stage does not change the handler (ADR-001/002) or lifecycle. Won/lost stay outcomes. A posted outcome filter is kept. A stale same-stage request is refused. A merge bumps the deal version and the stage audit follows the kept contact |
| REQ-016, REQ-020, REQ-022, REQ-026 (C-R2, C-R3) | Stalled-opportunity attention reason; pre-filled follow-up task after a logged interaction (rule-based proposals from `context/05_research/AI_AUTOMATION_RESEARCH.md`, implementation defaults pending OQ-015) | `crm/attention/services.py` `_stalled`, `Opportunity.stage_changed_at`, `crm/contacts/views.py` `followup_suggestion` | `tests/test_rule_automations.py` | Met as implementation defaults |
| REQ-016, REQ-026 (C-R1) | Explained priority score sorts within the existing severity groups. Turning it off restores age order. It does not change who is responsible and is not a ranking of people | `crm/attention/services.py` `_apply_priority`; Settings “Sort attention with an explained priority score” | `tests/test_priority_score.py` | Met as an implementation default. Weights are not a business approval |
| REQ-023 | Rules with trigger/conditions/action; enable/disable; execution records; disabled rules schedule nothing; preview; config history | `Rule`, `RuleVersion`, `RuleRun`, Automation screens | `test_preview_has_no_side_effects`, `test_disabled_sweep_rule_creates_nothing`, `test_opt_out_suppresses_and_disabled_rule_cancels_queued` | Met |
| REQ-024 (product) | Each customer company sets up its own install: company profile and logo, first-run checklist, company placeholders in customer email | `crm/core/views.py` `company_profile`, `brand_logo`, `setup_steps`; `BrandLogo` | `tests/test_company_profile.py` | Met as implementation default |
| REQ-003–006 (product) | Import an existing contact book from CSV with preview, validation and duplicate flags | `crm/contacts/importing.py`, Contacts → Import CSV | `tests/test_import.py` | Met as implementation default |
| REQ-005 (product) | Merge a duplicate into the kept record without losing history or bypassing ADR-001/002 | `crm/contacts/merging.py`, contact page "Possible duplicates" | `tests/test_merge.py` | Met as implementation default |
| NFR security (product) | Password reset by emailed link; optional or company-required two-step sign-in with recovery codes | `crm/accounts/views.py`, `crm/accounts/totp.py` | `tests/test_sign_in_security.py` | Met as implementation default; staff SMTP needs configuration per install |
| NFR operations (product) | Repeatable per-company install with HTTPS, encrypted backups, pruning and a documented restore drill | `Dockerfile`, `deploy/`, `scripts/new_company.sh`, `crm/core/backup_crypto.py` | `tests/test_backup_encryption.py`; `tests/test_operations.py`; isolated `backup_db`/`restore_db` on a throwaway SQLite file at 2026-11-13T03:10:20Z (workspace database untouched). Docker kit run locally 2026-11-13 verified encrypted backup, not a second-machine drill | Met as implementation default; no real server |
| REQ-024 | Configurable terminology and stages | Settings: lifecycle labels, stages | `test_relabelling_keeps_stable_codes_and_history` | Met |
| REQ-025 | Use the CrisGen design references | Vendored CrisGen UI 1.1; Drawer, Modal and Tabs via `static/crm/behaviors.js` | [UI_COMPONENTS.md](UI_COMPONENTS.md), `.cursor/rules/design-system.mdc` | Met for shell, tables, and sales overlays. Dropdown, popover, tooltip, select listbox, accordion and collapse are not wired |
| REQ-026 | Resurface forgotten clients, incl. toured with no follow-up; coverage | Attention reasons + coverage metric | `tests/test_attention.py` | Met |
| REQ-007–011 | Deferred items (portal, etc.) | Not built | — | Deferred by scope |
| NFR-001 | Authentication boundary | Login required everywhere; intake token-only | AT-007: `test_anonymous_users_are_sent_to_login`, `test_intake_token_grants_no_read_access` | Met |
| NFR-002 | Traceability | `AuditEvent` in the same transaction, request ids, assignment history | Audit screen; service tests | Met |
| NFR-003 | Reliable scheduled actions | DB job queue, leases, retries, dead letter, coalesced schedules | AT-011: `test_persisted_reminder_survives_restart`, `test_worker_crash_lease_recovery_and_no_double_execution` | Met |
| NFR-004 | Distinct work states | Empty vs filtered-empty, validation errors keep input, conflict messages, provider failure visible, DB busy message | `test_empty_and_filter_empty_states_are_distinct`, `test_invalid_capture_keeps_what_was_typed`, `test_stale_edit_is_rejected_not_overwritten` | Met; no loading states needed (no client-side fetches) |

## Acceptance catalog (context/10_validation/ACCEPTANCE_CATALOG.md)

| AT | Result | Tests |
|---|---|---|
| AT-001 | Passed | `test_simultaneous_claims_have_exactly_one_winner`, `test_second_claim_conflicts…`, `test_claim_replay…`, `test_claim_does_not_touch_source_or_introducer` |
| AT-002 | Passed | `test_transfer_keeps_sender_responsible_until_accepted`, `test_only_named_recipient_can_accept`, `test_decline_and_cancel…`, `test_stale_request…`, `test_release_requires_coordinator_acceptance` |
| AT-003 | Passed | `test_toured_client_without_task_appears_after_window`, `test_profile_view_and_notes_do_not_count_as_contact` |
| AT-004 | Passed (sandbox) | `test_sweep_is_idempotent_and_reassignment_reroutes`, `test_customer_reply_before_send…`, `test_opt_out…`, `test_provider_timeout_is_uncertain_and_not_retried` |
| AT-005 | Passed | `test_one_client_three_reasons_counts_once`, `test_coverage_zero_denominator_is_not_applicable`, report tests |
| AT-006 | Passed | `test_invalid_capture_keeps_what_was_typed`, `test_duplicate_is_shown_not_merged…`, `test_repeat_inquiry_reuses_identity…` |
| AT-007 | Passed | `test_anonymous_users_are_sent_to_login`, `test_csrf_is_enforced` |
| AT-008 | Passed | `test_watch_then_unwatch`, `test_watch_does_not_change_ownership` |
| AT-009 | Passed | `test_preview_has_no_side_effects`, `test_disabled_sweep_rule_creates_nothing`, `test_opt_out_suppresses_and_disabled_rule_cancels_queued` |
| AT-010 | Passed | `test_relabelling_keeps_stable_codes_and_history` |
| AT-011 | Passed | `test_persisted_reminder_survives_restart`, `test_worker_crash_lease_recovery_and_no_double_execution` |
| AT-012 | Passed (server-rendered states) | see NFR-004 |

## Not run / not available

- Real email provider delivery (no provider or credentials; sandbox only).
- MySQL (guide only; no MySQL server in the build environment).
- Usability testing with the sales team, and an assistive-technology audit. A keyboard, label, contrast, empty/error, and 390px pass on Today, the attention queue, Sales, Notifications, and Settings was recorded on 2026-11-13; that is not a substitute for the team pass.
- Load testing; behaviour above a single-office team size is unmeasured.
- Hosted CI: first runs on GitHub Actions passed on 2026-11-12 (head 0224dab, runs 43295590124 and 43295644932).

## 13 November 2026 hardening evidence

Current execution and exact check results: `context/09_development/CURRENT_RUN_REPORT.md`.

| Requirement | Added behavior | Regression evidence |
|---|---|---|
| REQ-020 / NFR-003 | Old worker completion cannot overwrite newer lease state or fail its customer message | `tests/test_worker_fencing.py` |
| REQ-018 / REQ-020 | Manual retries preserve inquiry stop checks and reject stale actions | `tests/test_comms_retry.py` |
| REQ-022 / NFR-002 | Inquiry/response chronology validated; spend and audit rollback together | `tests/test_reporting_integrity.py` |
| REQ-016 / REQ-026 | Agreed future contact pauses tour cadence but not urgent work | `tests/test_attention_agreement.py` |
| REQ-019 / REQ-026 | Unanswered inbound replies surface until later human-response evidence | `tests/test_inbound_attention.py` |
| REQ-026 | Digest counts new/continuing/resolved unique clients against prior delivered snapshot, including resolved-only digests; clients merged since the snapshot count as continuing | `tests/test_digest_changes.py`, `tests/test_pr4_review_fixes.py`; migration `automation.0003_digest_snapshots` |
| REQ-019 | Daily digest staff copy is filed or handed to staff mail, skipped when the setting is off, and creates no customer message | `tests/test_staff_digest.py`; migration `automation.0004_digest_staff_email` |
| REQ-019 / REQ-026 | The oldest unanswered reply anchors the wait; replies on an inquiry closed without response stay closed | `tests/test_pr4_review_fixes.py` |
| NFR reliability | A send job whose worker crashes on every attempt ends as *Delivery uncertain* (never auto-retried); stale results and expired leases are logged | `tests/test_pr4_review_fixes.py` |
| NFR-001 | A stage move without a CSRF token is refused. An agent cannot change the priority score or the staff digest setting. One person cannot see or dismiss another's notification. A stage label in the score is escaped. A clean database migration includes the digest email columns | `tests/test_slice_guards.py`; `tests/test_operations.py` `test_fresh_database_migrates_from_zero` |

Reply response matching uses contact chronology; there is no explicit reply-thread link. A linked awaiting inquiry avoids duplicate reply reasons. An unlinked inquiry cannot establish event identity. Digest resolution means departure from the recipient's queue, including reassignment; it does not assert task completion. Existing pre-migration digests have no snapshot; the first new digest establishes the baseline.

## 13 November 2026 sales board

Local evidence: pytest 216 passed, ruff clean, `makemigrations --check` clean, and `scripts/e2e.sh` 19 checks at 2026-11-13T03:01:43Z. Hosted CI was green on a824d13. Later commits are not claimed until GitHub Actions runs them.
