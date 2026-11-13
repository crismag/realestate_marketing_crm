# Installing the CRM for a new customer company

Each real estate company gets its **own copy**: its own server, database, domain, backups and keys. No data
is shared between companies. This guide takes about 30 minutes for someone comfortable with a Linux server.

## What you need

| Item | Notes |
|---|---|
| A small Linux server | 1 vCPU, 1–2 GB RAM, 20 GB disk is enough for an office of 50 staff. Ubuntu 24.04 LTS or Debian 12. Pick a region close to the office. |
| Docker Engine with the Compose plugin | `curl -fsSL https://get.docker.com \| sh` on a fresh server. |
| A domain name for the CRM | e.g. `crm.casarealty.ph`. Create a DNS **A** record pointing at the server's public IP. |
| Ports 80 and 443 open | Caddy uses them to obtain and renew the HTTPS certificate automatically. |
| The company administrator's email | They receive the first sign-in. |
| Optional: an SMTP account for staff email | For "Forgot your password?" links (e.g. the company's Google Workspace or Microsoft 365 SMTP relay, or a transactional email service). Customer emails stay in the sandbox regardless. |

## Steps

```bash
# 1. On the company's server, get the code (or copy a release archive).
git clone https://github.com/crismag/realestate_marketing_crm.git /srv/crm && cd /srv/crm

# 2. Create this company's configuration with fresh random secrets.
scripts/new_company.sh casa-realty crm.casarealty.ph admin@casarealty.ph
```

The script prints the **backup key**. Put it in the company's password manager now (and in yours, if you
support them). Without it, nobody can restore their backups.

```bash
# 3. Start the CRM (web, worker, hourly encrypted backups, HTTPS proxy).
cd deploy && docker compose --env-file .env up -d --build

# 4. Create the first administrator; the printed temporary password must be changed at first sign-in.
docker compose --env-file .env run --rm web manage create_admin --email admin@casarealty.ph --name "Office administrator" --generate

# 5. Check health (should print {"database": "ok", "worker_alive": true}).
curl -s https://crm.casarealty.ph/healthz
```

Give the administrator the address and temporary password over a different channel than each other (for
example the address by email and the password by phone). Their first screen shows **Set up your CRM** with
the five things to do; the [admin guide](ADMIN_GUIDE.md) walks through them.

## Optional settings in `deploy/.env`

| Setting | When |
|---|---|
| `CRM_STAFF_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD`, `CRM_STAFF_FROM_EMAIL` | To email password reset links to staff. Without it, an administrator resets passwords from *Settings → People*. |
| `CRM_INTAKE_TOKEN`, `CRM_INTAKE_POOL` | To let the company's website form create inquiries (`POST /api/intake/inquiries`). |
| `CRM_BACKUP_KEEP` | How many hourly backups to keep (default 72). |

After editing `.env`: `docker compose --env-file .env up -d`.

## Backups and the restore drill

- The `backup` service writes an **encrypted** backup every hour to the `crm-data` volume and keeps the newest
  `CRM_BACKUP_KEEP`.
- Copy backups off the server daily. For example with `rclone` to the company's cloud storage:
  `docker compose --env-file .env exec web sh -c 'ls /data/backups'` shows the files; mount or copy
  `/var/lib/docker/volumes/crm-<slug>_crm-data/_data/backups/` with your tool of choice. The files are
  encrypted, so ordinary cloud storage is fine.
- **Do a restore drill before go-live** and every quarter:

```bash
docker compose --env-file .env exec web python manage.py backup_db --verify /data/backups/<file>.sqlite3.enc
docker compose --env-file .env stop web worker backup
docker compose --env-file .env run --rm web manage restore_db /data/backups/<file>.sqlite3.enc --confirm <file>.sqlite3.enc
docker compose --env-file .env up -d
```

`restore_db` saves the current database as a `pre-restore` backup first, so a drill can be undone the same way.

## Upgrades

```bash
cd /srv/crm && docker compose -f deploy/docker-compose.yml --env-file deploy/.env exec web python manage.py backup_db
git pull
cd deploy && docker compose --env-file .env up -d --build   # migrations run automatically when web starts
```

## Before you hand it over

- [ ] HTTPS works and `http://` redirects to `https://`
- [ ] `/healthz` shows the worker alive
- [ ] The backup key is in the company's password manager, and a restore drill succeeded
- [ ] Backups are copied off the server
- [ ] The administrator signed in, changed the password and turned on two-step sign-in
- [ ] The company profile, timezone and currency are set
- [ ] `docker compose --env-file .env run --rm web manage check --deploy` shows no warnings you have not accepted

## What this kit does not do

- It does not send customer emails: those stay in the sandbox until a real provider is added and tested.
- It does not host several companies on one server behind one proxy. Use one server per company.
- It does not monitor the server for you. Point an uptime checker at `https://<domain>/healthz`.
