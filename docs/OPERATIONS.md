# Operations

## Processes

| Process | Command | Notes |
|---|---|---|
| Web | `python -m waitress --listen=127.0.0.1:8000 --threads=8 crm_project.wsgi:application` | Run one process; it is threaded. Static files are served by WhiteNoise after `collectstatic`. |
| Worker | `python manage.py run_worker` | Run exactly one. It polls the database job queue every `CRM_WORKER_POLL_SECONDS` (5 s), leases jobs for `CRM_WORKER_LEASE_SECONDS` (120 s) and stops cleanly on SIGTERM/SIGINT. |

Supervise both (systemd, supervisord, a container runtime). Example systemd units:

```ini
# /etc/systemd/system/crm-web.service
[Unit]
Description=Real Estate CRM web
After=network.target
[Service]
User=crm
WorkingDirectory=/srv/crm
EnvironmentFile=/srv/crm/.env
ExecStart=/srv/crm/.venv/bin/python -m waitress --listen=127.0.0.1:8000 --threads=8 crm_project.wsgi:application
Restart=always
[Install]
WantedBy=multi-user.target

# /etc/systemd/system/crm-worker.service  (same, with:)
ExecStart=/srv/crm/.venv/bin/python manage.py run_worker
```

## Health

`GET /healthz` (no sign-in) returns `{"database": "ok", "worker_alive": true}`. The worker writes a heartbeat
every loop; `worker_alive` turns false when no heartbeat arrived recently. The **Automation → Jobs** screen
shows the due backlog, failed and dead-lettered jobs with their errors, and lets an administrator retry or
cancel them.

What happens when things stop:

- **Worker stopped**: nothing is lost. Jobs and reminders are rows in the database; when the worker starts
  again it recovers expired leases, runs everything due, and coalesces missed sweeps into one run (no flood
  of duplicate reminders). Covered by `test_persisted_reminder_survives_restart` and
  `test_worker_crash_lease_recovery_and_no_double_execution`.
- **Worker crashed mid-job**: the lease expires and the job is retried. Logical keys stop the same reminder
  or customer message being created twice.
- **Database busy**: writes retry briefly; if still locked, the user sees "The database is busy. Nothing
  was saved" and can retry.

## Backup

```bash
python manage.py backup_db                 # writes var/backups/crm-<UTC timestamp>.sqlite3 + .json manifest
python manage.py backup_db --dir /mnt/backup/crm
python manage.py backup_db --verify /mnt/backup/crm/crm-20261113T020000000000Z.sqlite3
```

- Uses SQLite's online backup API, so it is consistent while the app and worker run.
- Each backup is integrity-checked, written with mode 0600 in a 0700 directory, and described by a manifest
  with its SHA-256, size and latest migrations.
- **Backups are not encrypted.** Copy them to encrypted, access-controlled storage and treat them as
  personal data.
- Suggested schedule (owner to confirm recovery targets, OQ-012): hourly during office hours plus nightly,
  keep 7 daily and 4 weekly copies, and copy off the server. Example cron:
  `0 * * * * cd /srv/crm && .venv/bin/python manage.py backup_db --dir /srv/crm-backups >> /var/log/crm-backup.log 2>&1`
- Pruning old backups is left to the operator (delete the `.sqlite3` and its `.json` together).

## Restore

1. Stop the web and worker processes.
2. Verify the file: `python manage.py backup_db --verify <backup>`.
3. Restore: `python manage.py restore_db <backup> --confirm <backup file name>`.
   The command refuses without the exact file name, refuses a backup whose checksum or integrity check
   fails, and first saves the current database as a `pre-restore` backup.
4. Run `python manage.py migrate` (needed only if the backup predates the code).
5. Start the processes and check `/healthz`.

The full cycle (backup → change → restore → restore the safety copy) and tamper detection are covered by
`tests/test_operations.py`. Practise a restore on a spare machine before relying on it.

## Upgrades

```bash
python manage.py backup_db
git pull && .venv/bin/pip install -r requirements.txt
python manage.py migrate && python manage.py collectstatic --noinput
# restart web and worker
```

## Logs

Both processes write one JSON object per line to stderr (`CRM_LOG_LEVEL`, default INFO). Passwords, tokens,
session and CSRF values are removed and email addresses masked. Each request carries an `X-Request-ID`,
also stored on audit rows.

## Customer email

Only the sandbox transport exists. Every automated customer email is written to `var/sandbox_mail/` as an
`.eml` file and shown in **Customer messages** as "Captured by sandbox (not sent)". Addresses at the
reserved domains `fail.invalid` and `timeout.invalid` simulate a provider rejection and an uncertain
outcome. Connecting a real provider is backlog work: implement a transport in `crm/comms/transports.py`
with delivery confirmation, signed callbacks and bounce handling, test it against the provider's sandbox,
then enable it deliberately.
