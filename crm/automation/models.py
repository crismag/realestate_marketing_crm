from __future__ import annotations

from django.conf import settings
from django.db import models

from crm.core import clock


class Rule(models.Model):
    """A catalogued automation rule (context AUTOMATION_CATALOG.md). Behaviour lives in code; config is versioned."""

    AUDIENCES = [("internal", "Internal notification"), ("customer", "Customer message")]

    key = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    audience = models.CharField(max_length=10, choices=AUDIENCES, default="internal")
    trigger = models.CharField(max_length=300)
    conditions = models.CharField(max_length=400)
    action = models.CharField(max_length=300)
    stop_policy = models.CharField(max_length=400)
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(default=clock.now)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["audience", "name"]

    def __str__(self):
        return self.name


class RuleVersion(models.Model):
    rule = models.ForeignKey(Rule, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    enabled = models.BooleanField()
    config = models.JSONField(default=dict)
    changed_at = models.DateTimeField(default=clock.now)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["rule", "version"], name="unique_rule_version")]


class Job(models.Model):
    """Durable unit of background work (database-backed queue with leases)."""

    STATUSES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed (will retry)"),
        ("dead", "Failed permanently"),
        ("cancelled", "Cancelled"),
    ]
    kind = models.CharField(max_length=60, db_index=True)
    payload = models.JSONField(default=dict)
    logical_key = models.CharField(max_length=200, unique=True, null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUSES, default="queued")
    run_at = models.DateTimeField(default=clock.now)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    lease_owner = models.CharField(max_length=80, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    result = models.JSONField(default=dict, blank=True)
    rule = models.ForeignKey(Rule, null=True, blank=True, on_delete=models.SET_NULL, related_name="jobs")
    rule_version = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=clock.now)
    updated_at = models.DateTimeField(default=clock.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "run_at"]), models.Index(fields=["status", "lease_expires_at"])]


class JobAttempt(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="attempt_log")
    attempt_no = models.PositiveIntegerField()
    worker_id = models.CharField(max_length=80)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=20, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]


class RuleRun(models.Model):
    """One evaluation of a rule (sweep), with what it matched and created."""

    rule = models.ForeignKey(Rule, on_delete=models.CASCADE, related_name="runs")
    rule_version = models.PositiveIntegerField()
    started_at = models.DateTimeField(default=clock.now, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    evaluated_for = models.DateTimeField(help_text="Clock time the evaluation used")
    matched = models.PositiveIntegerField(default=0)
    created = models.PositiveIntegerField(default=0)
    suppressed = models.PositiveIntegerField(default=0)
    outcome = models.CharField(max_length=20, default="running")
    error = models.TextField(blank=True)
    job = models.ForeignKey(Job, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-started_at", "-id"]


class Notification(models.Model):
    """Internal notification. Reading/dismissing never completes the underlying work."""

    STATUSES = [("delivered", "Delivered in app"), ("routing_gap", "No recipient (routing gap)")]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    status = models.CharField(max_length=12, choices=STATUSES, default="delivered")
    kind = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    reason = models.CharField(max_length=300, help_text="Why this was sent")
    contact = models.ForeignKey("contacts.Contact", null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    task = models.ForeignKey("work.Task", null=True, blank=True, on_delete=models.CASCADE, related_name="+")
    handover = models.ForeignKey("work.Handover", null=True, blank=True, on_delete=models.CASCADE, related_name="+")
    rule = models.ForeignKey(Rule, null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    rule_version = models.PositiveIntegerField(null=True, blank=True)
    logical_key = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(default=clock.now, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["recipient", "dismissed_at", "created_at"])]


class WorkerHeartbeat(models.Model):
    worker_id = models.CharField(max_length=80, unique=True)
    hostname = models.CharField(max_length=120)
    pid = models.PositiveIntegerField()
    started_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    jobs_processed = models.PositiveIntegerField(default=0)
    state = models.CharField(max_length=20, default="running")

    class Meta:
        ordering = ["-last_seen_at"]


class ScheduleState(models.Model):
    """Periodic schedule bookkeeping (attention sweep, digests). Catch-up policy: coalesce missed runs into one."""

    key = models.CharField(max_length=80, unique=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField()
