# Security notes

Scope: an internal CRM for one company workspace. Every signed-in colleague may see every customer by
design (REQ-001/002); security here means keeping everyone else out, protecting integrity of
responsibility changes, and not leaking personal data.

## Controls in place (with tests)

| Area | Control | Evidence |
|---|---|---|
| Authentication boundary | Django `LoginRequiredMiddleware`: every page needs a session except sign-in, `/healthz` and the token-authenticated intake API | `tests/test_web.py::test_anonymous_users_are_sent_to_login` |
| Passwords | Argon2id hashing; minimum 12 characters, common/numeric/similarity validators; temporary passwords force a change at next sign-in | `test_must_change_password_blocks_other_pages`, `test_create_admin_has_no_default_password` |
| No default credentials | `create_admin` prompts or generates a one-time password; `seed_demo` uses `CRM_DEMO_PASSWORD` or a random one and refuses `CRM_ENV=production` | `tests/test_operations.py` |
| Brute force | Lockout after 5 failures per account within 15 minutes (and 20 per IP) | `test_login_throttling_locks_after_repeated_failures` |
| Sessions | HttpOnly, SameSite=Lax, Secure when `CRM_SECURE_COOKIES=1` (default in production); session key rotated at sign-in; sign-out is POST and flushes the server session; deactivating a user or resetting their password ends their sessions | `test_security_headers_and_cookie_flags`, `test_logout_requires_post_and_ends_session`, `test_deactivating_a_user_ends_their_sessions` |
| CSRF | Django CSRF middleware on every form, including sign-in | `test_csrf_is_enforced` |
| Open redirects | `next` targets checked with `url_has_allowed_host_and_scheme` | `test_open_redirect_is_refused` |
| Mass assignment | Explicit form fields and service allow-lists; responsibility, lifecycle and archive change only through their own audited operations | `test_mass_assignment_cannot_change_responsibility_via_edit` |
| Integrity of responsibility | Optimistic versions on contacts, assignments, tasks, opportunities, settings and templates; claims and acceptances are conditional updates; only the named recipient (or the destination pool's coordinator) can accept. A posted version, pool id, team id, or person id that does not fit in a signed 64-bit integer is refused before it reaches SQLite | `tests/test_responsibility.py`, `tests/test_concurrency.py`, `tests/test_input_bounds.py` |
| Admin-only settings | Users, settings, pools, teams and sources can only be changed by administrators (reads stay open, per REQ-001) | `test_non_admin_cannot_manage_users_or_settings` |
| XSS | Django auto-escaping everywhere; no `|safe` on user data; Content-Security-Policy `script-src 'self'; style-src 'self'` with no inline scripts or styles (enforced by a template test) | `test_user_content_is_escaped`, `test_templates_have_no_inline_styles_or_scripts`, e2e console check |
| SQL injection | ORM / parameterised queries only | `test_search_input_is_not_sql` |
| CSV formula injection | Cells starting with `= + - @` (and tab/CR) are prefixed with `'` on export | `test_csv_export_neutralises_formulas` |
| Security headers | CSP, `X-Frame-Options: DENY`, `frame-ancestors 'none'`, `nosniff`, `Referrer-Policy: same-origin`, `Permissions-Policy`, `Cross-Origin-Resource-Policy`; HSTS/SSL redirect via env | `test_security_headers_and_cookie_flags`, `scripts/e2e.sh` (`check --deploy`) |
| Intake API | Disabled unless `CRM_INTAKE_TOKEN` is set; bearer token compared in constant time; 16 KB body limit; a non-numeric Content-Length is a 400 and stores nothing; validated fields; idempotent by `external_id`; grants no read access | `tests/test_intake.py`, `tests/test_input_bounds.py` |
| Logs | JSON logs with a redacting filter: password/secret/token/session/cookie/csrf/key fields removed; email addresses masked in messages and arguments | `test_logs_redact_secrets_and_emails` |
| Audit | Append-only `AuditEvent` rows in the same transaction as each consequential change (actor, time, request id) | Settings → Audit log; service tests |
| Customer messaging | Sandbox transport only; captured messages are labelled "not sent"; stop policies re-checked at send time | `tests/test_automation.py` |
| Dependencies | Pinned in `requirements*.txt`; `pip-audit` in CI (no known vulnerabilities at the time of this build) | CI workflow |
| Secrets | `CRM_SECRET_KEY` required in production; in development a random key is generated into `var/secret_key` (0600). `.env`, `var/`, databases and backups are git-ignored | `.gitignore` |

## Things this build does NOT do

- **SQLite and backups are not encrypted.** Use full-disk encryption on the server and keep the `var/`
  directory and backup destination readable only by the service account. Treat backups as personal data.
- No multi-factor authentication, single sign-on or password-reset email (administrators reset passwords).
- No per-record access restrictions; by requirement, all signed-in staff see all customers.
- No real email provider, so no SPF/DKIM, bounce or webhook handling yet. A provider adapter must add
  signature verification and replay protection for callbacks before going live.
- Login throttling is per account and IP in the database; there is no CAPTCHA or global rate limiter.
  Put the app behind a reverse proxy that can rate-limit if it is reachable from outside the office.
- No data-retention or deletion workflow beyond archiving (retention policy is an open decision).

## Reporting a problem

Raise it with the workspace owner. Do not paste customer data into issues or chat.
