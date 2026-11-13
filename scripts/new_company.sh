#!/usr/bin/env bash
# Prepare the configuration for one customer company's install (run on that company's server).
#   scripts/new_company.sh <company-slug> <domain> [admin-email]
# Writes deploy/.env with fresh random secrets. Refuses to overwrite an existing one.
set -euo pipefail
cd "$(dirname "$0")/.."

slug="${1:-}"; domain="${2:-}"; admin="${3:-}"
if [[ ! "$slug" =~ ^[a-z0-9][a-z0-9-]{1,30}$ || -z "$domain" ]]; then
  echo "Usage: $0 <company-slug, e.g. casa-realty> <domain, e.g. crm.casarealty.ph> [admin-email]" >&2
  exit 2
fi
env_file="deploy/.env"
if [[ -e "$env_file" ]]; then
  echo "$env_file already exists. This server is already set up; edit that file instead." >&2
  exit 1
fi
rand() { python3 -c "import secrets,base64,sys; print(base64.urlsafe_b64encode(secrets.token_bytes(int(sys.argv[1]))).decode())" "$1"; }
umask 077
cat > "$env_file" <<ENV
# $slug: generated $(date -u +%Y-%m-%dT%H:%MZ). Keep this file private; never commit it.
CRM_COMPANY_SLUG=$slug
CRM_DOMAIN=$domain
CRM_SECRET_KEY=$(rand 48)
# Backups are encrypted with this key. Store a copy in the company's password manager:
# without it, the backups cannot be restored by anyone.
CRM_BACKUP_KEY=$(rand 32)
CRM_BACKUP_KEEP=72
CRM_LOG_LEVEL=INFO
# Staff email for password reset links (optional but recommended):
CRM_STAFF_SMTP_HOST=
CRM_STAFF_SMTP_PORT=587
CRM_STAFF_SMTP_USER=
CRM_STAFF_SMTP_PASSWORD=
CRM_STAFF_FROM_EMAIL=
# Website form intake (optional): set a long random token to enable POST /api/intake/inquiries
CRM_INTAKE_TOKEN=
CRM_INTAKE_POOL=
ENV
echo "Wrote $env_file (mode 600)."
echo
echo "IMPORTANT: copy this backup key into the company's password manager now:"
grep '^CRM_BACKUP_KEY=' "$env_file" | cut -d= -f2-
echo
echo "Next:"
echo "  cd deploy && docker compose --env-file .env up -d --build"
if [[ -n "$admin" ]]; then
  echo "  docker compose --env-file .env run --rm web manage create_admin --email $admin --name 'Office administrator' --generate"
else
  echo "  docker compose --env-file .env run --rm web manage create_admin --email <admin email> --generate"
fi
echo "Then open https://$domain and follow 'Set up your CRM' on the Today page."
