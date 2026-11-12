from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q

from crm.core import clock


class Pool(models.Model):
    """Shared queue of relationships awaiting an individual handler (ADR-002)."""

    name = models.CharField(max_length=100, unique=True)
    team = models.ForeignKey("accounts.Team", null=True, blank=True, on_delete=models.SET_NULL, related_name="pools")
    coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="coordinated_pools",
        help_text="Accountable for pool attention. Operational responsibility, not an access permission.",
    )
    backup_coordinator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def accountable_users(self):
        return [u for u in (self.coordinator, self.backup_coordinator) if u is not None and u.is_active]


class Assignment(models.Model):
    """Current relationship responsibility: exactly one person OR one pool. Versioned for atomic transitions."""

    KINDS = [("person", "Person"), ("pool", "Pool")]

    contact = models.OneToOneField("contacts.Contact", on_delete=models.PROTECT, related_name="assignment")
    kind = models.CharField(max_length=10, choices=KINDS)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="assignments")
    pool = models.ForeignKey(Pool, null=True, blank=True, on_delete=models.PROTECT, related_name="assignments")
    since = models.DateTimeField(default=clock.now)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(Q(kind="person", user__isnull=False, pool__isnull=True) | Q(kind="pool", pool__isnull=False, user__isnull=True)),
                name="assignment_person_xor_pool",
            )
        ]
        indexes = [models.Index(fields=["kind", "user"]), models.Index(fields=["kind", "pool"])]

    @property
    def holder(self):
        return self.user if self.kind == "person" else self.pool

    def describe(self) -> str:
        return f"{self.user}" if self.kind == "person" else f"Pool: {self.pool}"


class AssignmentEvent(models.Model):
    """Append-only responsibility history."""

    TYPES = [
        ("created", "Assigned at capture"),
        ("claimed", "Claimed from pool"),
        ("handover_accepted", "Handover accepted"),
        ("release_accepted", "Release to pool accepted"),
    ]
    contact = models.ForeignKey("contacts.Contact", on_delete=models.PROTECT, related_name="assignment_events")
    event_type = models.CharField(max_length=30, choices=TYPES)
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    from_pool = models.ForeignKey(Pool, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    to_pool = models.ForeignKey(Pool, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+")
    reason = models.CharField(max_length=300, blank=True)
    handover = models.ForeignKey("Handover", null=True, blank=True, on_delete=models.PROTECT, related_name="assignment_events")
    operation_key = models.CharField(max_length=80, unique=True)
    version_after = models.PositiveIntegerField()
    occurred_at = models.DateTimeField(default=clock.now, db_index=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]


class Handover(models.Model):
    """Client transfer (person->person) or release (person->pool). Sender stays accountable until accepted (ADR-001/002)."""

    KINDS = [("transfer", "Transfer to colleague"), ("release", "Release to pool")]
    STATES = [
        ("requested", "Awaiting acceptance"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("cancelled", "Cancelled"),
        ("stale", "Stale (responsibility changed)"),
    ]

    contact = models.ForeignKey("contacts.Contact", on_delete=models.PROTECT, related_name="handovers")
    kind = models.CharField(max_length=10, choices=KINDS)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="handovers_sent")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="handovers_received")
    pool = models.ForeignKey(Pool, null=True, blank=True, on_delete=models.PROTECT, related_name="releases")
    expected_version = models.PositiveIntegerField()
    state = models.CharField(max_length=12, choices=STATES, default="requested", db_index=True)
    reason = models.CharField(max_length=300)
    context = models.TextField(blank=True, help_text="Next-action context for the recipient")
    requested_at = models.DateTimeField(default=clock.now)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    decision_note = models.CharField(max_length=300, blank=True)
    # Portable "one open handover per contact" guard: set to contact id while
    # requested, NULL otherwise. Unique NULLs are allowed on SQLite and MySQL.
    open_guard = models.BigIntegerField(null=True, blank=True, unique=True, editable=False)

    class Meta:
        ordering = ["-requested_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(kind="transfer", recipient__isnull=False, pool__isnull=True) | Q(kind="release", pool__isnull=False, recipient__isnull=True)),
                name="handover_kind_destination",
            )
        ]

    def destination_label(self) -> str:
        return str(self.recipient) if self.kind == "transfer" else f"Pool: {self.pool}"


class HandoverTaskDisposition(models.Model):
    DISPOSITIONS = [("keep", "Keep current assignee"), ("transfer", "Reassign to new handler on acceptance")]
    handover = models.ForeignKey(Handover, on_delete=models.CASCADE, related_name="task_dispositions")
    task = models.ForeignKey("Task", on_delete=models.PROTECT, related_name="+")
    disposition = models.CharField(max_length=10, choices=DISPOSITIONS)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["handover", "task"], name="unique_handover_task")]


class Task(models.Model):
    """A next action. The assignee can differ from the relationship handler."""

    KINDS = [
        ("follow_up", "Follow-up"),
        ("call", "Call"),
        ("meeting", "Meeting / tour"),
        ("promise", "Promise to customer"),
        ("admin", "Admin"),
    ]
    STATUSES = [("open", "Open"), ("done", "Done"), ("cancelled", "Cancelled")]

    contact = models.ForeignKey("contacts.Contact", on_delete=models.PROTECT, related_name="tasks")
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=KINDS, default="follow_up")
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tasks")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(default=clock.now)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    original_due_at = models.DateTimeField(null=True, blank=True)
    replan_count = models.PositiveIntegerField(default=0)
    last_replan_reason = models.CharField(max_length=200, blank=True)
    critical = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUSES, default="open", db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    completion_note = models.CharField(max_length=300, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["due_at", "id"]
        indexes = [models.Index(fields=["assignee", "status", "due_at"]), models.Index(fields=["contact", "status"])]

    def is_overdue(self, now) -> bool:
        return self.status == "open" and self.due_at is not None and self.due_at < now
