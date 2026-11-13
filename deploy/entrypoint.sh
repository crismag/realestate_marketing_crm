#!/bin/sh
# Container entrypoint: web | worker | backup | manage <args>
set -eu
cd /app
case "${1:-web}" in
  web)
    python manage.py migrate --noinput -v1
    exec python -m waitress --listen=0.0.0.0:8000 --threads="${CRM_WEB_THREADS:-8}" \
      --trusted-proxy='*' --trusted-proxy-headers='x-forwarded-proto x-forwarded-for' --clear-untrusted-proxy-headers \
      crm_project.wsgi:application
    ;;
  worker)
    # Wait for the web container to apply migrations before processing jobs.
    until python manage.py migrate --check >/dev/null 2>&1; do echo "worker: waiting for migrations"; sleep 3; done
    exec python manage.py run_worker
    ;;
  backup)
    # Hourly encrypted backup, keeping the newest CRM_BACKUP_KEEP copies (default 72 = three days of hours).
    until python manage.py migrate --check >/dev/null 2>&1; do echo "backup: waiting for migrations"; sleep 10; done
    while true; do
      python manage.py backup_db --keep "${CRM_BACKUP_KEEP:-72}" || echo "backup: FAILED (see above)"
      sleep "${CRM_BACKUP_INTERVAL_SECONDS:-3600}"
    done
    ;;
  manage)
    shift
    exec python manage.py "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
