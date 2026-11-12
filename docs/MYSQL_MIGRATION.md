# Moving from SQLite to MySQL

SQLite is the right default for one office team on one server. Move to MySQL 8.0+ (or MariaDB 10.6+)
when you need more than one web server, many concurrent writers, or managed database backups.

## What was done to keep this easy

- All business logic uses the Django ORM. The only raw SQL is the `SELECT 1` health check and `crm/core/backup.py` (SQLite-only
  backup tooling) and the SQLite connection settings.
- Concurrency control is portable: optimistic `version` columns and conditional `UPDATE … WHERE version = n`,
  unique constraints for idempotency (`operation_key`, `logical_key`, `external_key`) and a nullable unique
  `open_guard` column for "one open handover per contact" (no partial indexes, which MySQL lacks).
- Money is stored as integer minor units; all times are stored in UTC.
- Job leasing uses conditional updates, not `SELECT … FOR UPDATE SKIP LOCKED`, so it works on both.
- Check constraints are declared through Django (`CheckConstraint`), which MySQL 8.0.16+ enforces.

## Steps

1. Create the database with a utf8mb4 collation:
   ```sql
   CREATE DATABASE crm CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
   CREATE USER 'crm'@'%' IDENTIFIED BY '<strong password>';
   GRANT ALL PRIVILEGES ON crm.* TO 'crm'@'%';
   ```
2. Install a driver: add `mysqlclient` (needs MySQL client headers) to `requirements.txt`.
3. Change `DATABASES` in `crm_project/settings.py` behind an env switch, for example:
   ```python
   if os.environ.get("CRM_DB_ENGINE") == "mysql":
       DATABASES = {"default": {
           "ENGINE": "django.db.backends.mysql",
           "NAME": os.environ["CRM_DB_NAME"], "USER": os.environ["CRM_DB_USER"],
           "PASSWORD": os.environ["CRM_DB_PASSWORD"], "HOST": os.environ.get("CRM_DB_HOST", "127.0.0.1"),
           "PORT": os.environ.get("CRM_DB_PORT", "3306"),
           "OPTIONS": {"charset": "utf8mb4", "isolation_level": "read committed",
                       "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
           "CONN_MAX_AGE": 60, "ATOMIC_REQUESTS": False,
       }}
   ```
   `read committed` matters: the conditional-update pattern relies on seeing the latest committed row.
4. Create the schema: `python manage.py migrate` against the empty MySQL database.
5. Copy the data with the app stopped:
   ```bash
   # from SQLite
   python manage.py dumpdata --natural-foreign --exclude contenttypes --exclude auth.permission \
          --exclude sessions --indent 0 -o crm-data.json
   # to MySQL (CRM_DB_ENGINE=mysql …)
   python manage.py loaddata crm-data.json
   ```
   The dump contains personal data: keep it on encrypted storage and delete it afterwards.
6. Run the test suite against MySQL (`CRM_DB_ENGINE=mysql … pytest`). `tests/test_concurrency.py` is the
   important one: it proves single-winner claims and acceptances with real concurrent connections.
7. Replace `backup_db`/`restore_db` with MySQL tooling (`mysqldump --single-transaction` or managed
   snapshots). The SQLite commands refuse to run against another database engine.
8. You can now run several web processes. Keep **one** worker process unless you have tested multiple
   workers (the leasing is designed for it, but it has only been exercised on SQLite).

## Things to re-check on MySQL

- Case-insensitive lookups: `display_name__iexact` and search use the collation; `utf8mb4_0900_ai_ci`
  is also accent-insensitive, which changes duplicate-name matching slightly.
- `TextField` columns cannot carry unique indexes on MySQL; none do today.
- Datetime precision: Django uses `DATETIME(6)` on MySQL, matching SQLite microseconds.
- The SQLite-specific `init_command` (WAL, busy timeout) must not be sent to MySQL.
