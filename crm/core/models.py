from __future__ import annotations

from django.conf import settings
from django.db import models

from . import clock


class AuditEvent(models.Model):
    """Append-only record of consequential mutations (NFR-002)."""

    ACTOR_KINDS = [("user", "User"), ("system", "System"), ("worker", "Worker")]

    occurred_at = models.DateTimeField(default=clock.now, db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    actor_kind = models.CharField(max_length=16, choices=ACTOR_KINDS, default="user")
    action = models.CharField(max_length=64, db_index=True)
    object_type = models.CharField(max_length=64)
    object_id = models.CharField(max_length=64)
    contact = models.ForeignKey("contacts.Contact", null=True, blank=True, on_delete=models.PROTECT, related_name="audit_events")
    summary = models.CharField(max_length=300)
    data = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=36, blank=True)

    class Meta:
        indexes = [models.Index(fields=["object_type", "object_id"]), models.Index(fields=["contact", "occurred_at"])]
        ordering = ["-occurred_at", "-id"]

    def __str__(self):
        return f"{self.occurred_at:%Y-%m-%d %H:%M} {self.action} {self.summary}"


class WorkspaceSettings(models.Model):
    """Singleton (pk=1) holding the versioned workspace policy."""

    policy = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(default=clock.now)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="workspace_settings_singleton")]


class SettingsVersion(models.Model):
    version = models.PositiveIntegerField(unique=True)
    policy = models.JSONField()
    changed_at = models.DateTimeField(default=clock.now)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-version"]


class BrandLogo(models.Model):
    """Singleton (pk=1): the company logo, stored in the database so backups carry it."""

    content_type = models.CharField(max_length=40)
    data = models.BinaryField()
    sha256 = models.CharField(max_length=64)
    uploaded_at = models.DateTimeField(default=clock.now)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="brand_logo_singleton")]
