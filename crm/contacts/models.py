from __future__ import annotations

import re
import unicodedata

from django.conf import settings
from django.db import models

from crm.core import clock
from crm.core.policy import CHANNELS, INTERACTION_TYPES

LIFECYCLES = [("lead", "Lead"), ("prospect", "Prospect"), ("client", "Client")]
DISPOSITIONS = [("active", "Active"), ("nurture", "Nurture"), ("inactive", "Inactive"), ("disqualified", "Disqualified")]


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def name_key(value: str | None) -> str:
    """Order-insensitive name key: "Smith, John" and "john  SMITH" both give "john smith"."""
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    words = re.findall(r"[a-z0-9]+", text)
    return " ".join(sorted(words))[:150]


def normalize_phone(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits[-10:] if len(digits) >= 7 else digits


class Source(models.Model):
    KINDS = [
        ("website", "Website"),
        ("walk_in", "Walk-in"),
        ("referral", "Referral"),
        ("roadshow", "Roadshow / event"),
        ("social", "Social media"),
        ("search", "Search"),
        ("other", "Other"),
    ]
    code = models.SlugField(max_length=50, unique=True)
    label = models.CharField(max_length=100)
    kind = models.CharField(max_length=20, choices=KINDS, default="other")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return self.label


class Contact(models.Model):
    """Durable customer identity. Lifecycle, responsibility and attention are separate dimensions."""

    display_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email_normalized = models.CharField(max_length=254, blank=True, db_index=True, editable=False)
    phone_normalized = models.CharField(max_length=20, blank=True, db_index=True, editable=False)
    name_key = models.CharField(max_length=150, blank=True, db_index=True, editable=False,
                                help_text="Lowercased, accent-free, word-sorted name for duplicate matching")
    lifecycle = models.CharField(max_length=20, choices=LIFECYCLES, default="lead", db_index=True)
    disposition = models.CharField(max_length=20, choices=DISPOSITIONS, default="active")
    disposition_reason = models.CharField(max_length=200, blank=True)
    source = models.ForeignKey(Source, null=True, blank=True, on_delete=models.PROTECT, related_name="contacts")
    source_detail = models.CharField(max_length=200, blank=True, help_text="Campaign, event or page")
    introducer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="introduced_contacts",
        help_text="Staff member who introduced/referred the contact. Not ownership and not commission.",
    )
    referred_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals")
    interests = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    email_opt_out = models.BooleanField(default=False)
    email_opt_out_at = models.DateTimeField(null=True, blank=True)
    preferred_channel = models.CharField(max_length=20, choices=CHANNELS, blank=True)
    next_contact_agreed_at = models.DateTimeField(
        null=True, blank=True, help_text="Customer-requested later contact date; suppresses routine inactivity reminders"
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(default=clock.now, db_index=True)
    updated_at = models.DateTimeField(default=clock.now)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["display_name", "id"]
        indexes = [models.Index(fields=["lifecycle", "disposition"]), models.Index(fields=["display_name"])]

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        self.email_normalized = normalize_email(self.email)
        self.phone_normalized = normalize_phone(self.phone)
        self.name_key = name_key(self.display_name)
        super().save(*args, **kwargs)

    @property
    def is_active_relationship(self) -> bool:
        return self.archived_at is None and self.disposition in ("active", "nurture")


class Inquiry(models.Model):
    STATUSES = [("awaiting", "Awaiting response"), ("responded", "Responded"), ("closed", "Closed without response")]

    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="inquiries")
    source = models.ForeignKey(Source, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    channel = models.CharField(max_length=20, choices=CHANNELS, default="other")
    message = models.TextField(blank=True)
    received_at = models.DateTimeField(default=clock.now, db_index=True)
    recorded_at = models.DateTimeField(default=clock.now)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=20, choices=STATUSES, default="awaiting", db_index=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    response_interaction = models.ForeignKey("Interaction", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    external_key = models.CharField(max_length=120, null=True, blank=True, unique=True, help_text="Intake idempotency key")

    class Meta:
        ordering = ["-received_at", "-id"]


class Interaction(models.Model):
    """Human interaction evidence. Profile views and automated emails are never interactions."""

    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="interactions")
    kind = models.CharField(max_length=30, choices=INTERACTION_TYPES)
    channel = models.CharField(max_length=20, choices=CHANNELS, default="phone")
    summary = models.TextField()
    occurred_at = models.DateTimeField(db_index=True)
    recorded_at = models.DateTimeField(default=clock.now)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="interactions")
    inquiry = models.ForeignKey(Inquiry, null=True, blank=True, on_delete=models.SET_NULL, related_name="responses")

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [models.Index(fields=["contact", "kind", "occurred_at"])]


class Opportunity(models.Model):
    OUTCOMES = [("open", "Open"), ("won", "Won"), ("lost", "Lost")]

    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="opportunities")
    title = models.CharField(max_length=200)
    stage = models.CharField(max_length=40, default="new")
    stage_changed_at = models.DateTimeField(null=True, blank=True, help_text="When the stage last actually changed")
    outcome = models.CharField(max_length=10, choices=OUTCOMES, default="open", db_index=True)
    amount_minor = models.BigIntegerField(null=True, blank=True, help_text="Integer minor units (e.g. cents)")
    currency = models.CharField(max_length=3, blank=True)
    expected_close = models.DateField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    outcome_reason = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(default=clock.now)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount_minor__isnull=True) | models.Q(amount_minor__gte=0), name="opportunity_amount_nonnegative"),
        ]


class Watch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watches")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="watches")
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(default=clock.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "contact"], name="unique_watch")]
