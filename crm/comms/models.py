from __future__ import annotations

from django.conf import settings
from django.db import models

from crm.core import clock


class MessageTemplate(models.Model):
    """Customer-facing email template. Only {{ placeholders }} from ALLOWED_FIELDS are substituted."""

    ALLOWED_FIELDS = ("customer_name", "handler_name", "workspace_name")

    key = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=120)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(default=clock.now)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OutboundMessage(models.Model):
    """A customer-facing message and its real delivery state.

    ``sandbox_captured`` means the local sandbox transport stored it; nothing
    left this machine. It is never shown as a provider delivery.
    """

    STATUSES = [
        ("scheduled", "Scheduled"),
        ("suppressed", "Suppressed by stop policy"),
        ("sandbox_captured", "Captured by sandbox (not sent)"),
        ("delivered", "Delivered by provider"),
        ("failed", "Failed"),
        ("uncertain", "Delivery uncertain"),
        ("cancelled", "Cancelled"),
    ]

    contact = models.ForeignKey("contacts.Contact", on_delete=models.PROTECT, related_name="outbound_messages")
    template = models.ForeignKey(MessageTemplate, null=True, on_delete=models.PROTECT, related_name="+")
    template_version = models.PositiveIntegerField(null=True)
    rule = models.ForeignKey("automation.Rule", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    rule_version = models.PositiveIntegerField(null=True, blank=True)
    channel = models.CharField(max_length=10, default="email")
    to_address = models.CharField(max_length=254, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    logical_key = models.CharField(max_length=200, unique=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="scheduled", db_index=True)
    status_reason = models.CharField(max_length=300, blank=True)
    transport = models.CharField(max_length=20, default="sandbox")
    provider_ref = models.CharField(max_length=120, blank=True)
    scheduled_for = models.DateTimeField(default=clock.now)
    attempted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=clock.now)

    class Meta:
        ordering = ["-created_at", "-id"]
