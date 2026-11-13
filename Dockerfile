# Real Estate CRM: one image for the web process, the worker and scheduled backups.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    CRM_ENV=production CRM_VAR_DIR=/data CRM_DB_PATH=/data/crm.sqlite3 CRM_BACKUP_DIR=/data/backups \
    CRM_STATIC_ROOT=/app/staticfiles

RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin crm
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY --chown=crm:crm . .
# Static files are built into the image; a throwaway key is used only for this build step.
RUN CRM_SECRET_KEY=build-only-not-secret CRM_VAR_DIR=/tmp/build python manage.py collectstatic --noinput -v0 \
    && mkdir -p /data && chown crm:crm /data && rm -rf /tmp/build
USER crm
VOLUME ["/data"]
EXPOSE 8000
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["web"]
