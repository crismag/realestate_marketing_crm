"""Deployment checks (run by `manage.py check --deploy`)."""
from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.security, deploy=True)
def backup_and_mail_settings(app_configs, **kwargs):
    issues = []
    if not getattr(settings, "CRM_BACKUP_KEY", ""):
        issues.append(Warning("Backups are not encrypted.", hint="Set CRM_BACKUP_KEY (manage.py backup_key) and keep a copy "
                              "of the key away from the server.", id="crm.W001"))
    if not getattr(settings, "CRM_STAFF_SMTP_HOST", ""):
        issues.append(Warning("Staff email is not configured, so password reset links are not emailed.",
                              hint="Set CRM_STAFF_SMTP_HOST and related settings, or reset passwords as an administrator.",
                              id="crm.W002"))
    return issues
