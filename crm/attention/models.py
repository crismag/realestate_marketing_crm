from __future__ import annotations

from django.conf import settings
from django.db import models

from crm.core import clock


class Snooze(models.Model):
    """Hides one attention reason for a contact until a time. Never rewrites due dates or contact history."""

    contact = models.ForeignKey("contacts.Contact", on_delete=models.CASCADE, related_name="snoozes")
    reason_code = models.CharField(max_length=40)
    until = models.DateTimeField()
    note = models.CharField(max_length=300)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(default=clock.now)
    cleared_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["contact", "reason_code", "until"])]
