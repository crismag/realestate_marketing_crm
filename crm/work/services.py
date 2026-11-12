"""Responsibility, shared pools, handovers and tasks (MOD-002).

Approved rules implemented here:
- ADR-001: the sender stays responsible until the recipient explicitly accepts.
- ADR-002: exclusive atomic claims; release to a pool is a handover accepted by
  the pool coordinator; overdue work never removes ownership automatically.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import IntegrityError
from django.db.models import F

from crm.automation.queue import emit
from crm.core import clock
from crm.core.db import write_transaction
from crm.core.errors import ConflictError, DomainError, InvalidTransition, NotAllowed
from crm.core.services import audit

from .models import Assignment, AssignmentEvent, Handover, HandoverTaskDisposition, Pool, Task


@dataclass
class ClaimResult:
    assignment: Assignment
    replayed: bool = False


def claim(contact, *, actor, expected_version: int, operation_id: str) -> ClaimResult:
    """Atomically claim a pool-held contact. First successful claim wins; others get ConflictError."""
    if not operation_id or len(operation_id) > 64:
        raise DomainError("Missing operation id.", code="operation_id_required")
    op_key = f"claim:{operation_id}"

    def run():
        prior = AssignmentEvent.objects.filter(operation_key=op_key).first()
        if prior is not None:
            if prior.actor_id != actor.pk or prior.contact_id != contact.pk:
                raise ConflictError("This operation id was already used for a different request.")
            return ClaimResult(Assignment.objects.get(contact=contact), replayed=True)
        current = Assignment.objects.select_related("user", "pool").get(contact=contact)
        if current.kind != "pool":
            raise ConflictError(
                f"Already claimed: {current.describe()} is responsible.", code="already_claimed",
                details={"current": current.describe()},
            )
        now = clock.now()
        won = Assignment.objects.filter(pk=current.pk, kind="pool", version=expected_version).update(
            kind="person", user=actor, pool=None, since=now, version=F("version") + 1
        )
        if won != 1:
            latest = Assignment.objects.select_related("user", "pool").get(pk=current.pk)
            raise ConflictError(
                f"Someone else changed this assignment first. Current: {latest.describe()}.", code="stale_assignment",
                details={"current": latest.describe()},
            )
        AssignmentEvent.objects.create(
            contact=contact, event_type="claimed", from_pool=current.pool, to_user=actor, actor=actor,
            reason="Claimed from shared pool", operation_key=op_key, version_after=expected_version + 1, occurred_at=now,
        )
        _mark_open_handovers_stale(contact, actor, "Responsibility changed by a pool claim")
        audit("assignment.claimed", contact, f"{actor} claimed from pool {current.pool}", actor=actor, contact=contact)
        emit("assignment_changed", contact_id=contact.pk, to_user_id=actor.pk, event_key=f"claim:{operation_id}")
        return ClaimResult(Assignment.objects.select_related("user").get(pk=current.pk))

    try:
        return write_transaction(run)
    except IntegrityError:
        # Concurrent replay of the same operation id: report the stored outcome.
        if AssignmentEvent.objects.filter(operation_key=op_key, actor=actor).exists():
            return ClaimResult(Assignment.objects.get(contact=contact), replayed=True)
        raise


def _mark_open_handovers_stale(contact, actor, note: str):
    for handover in Handover.objects.filter(contact=contact, state="requested"):
        Handover.objects.filter(pk=handover.pk, state="requested").update(
            state="stale", decided_at=clock.now(), decision_note=note[:300], open_guard=None
        )
        audit("handover.stale", handover, note, actor=actor, contact=contact)
        emit("handover_closed", handover_id=handover.pk, state="stale")


def can_initiate_handover(assignment: Assignment, user) -> bool:
    if assignment.kind == "person":
        return assignment.user_id == user.pk
    return user in assignment.pool.accountable_users()


def request_handover(contact, *, actor, kind: str, recipient=None, pool: Pool | None = None, reason: str,
                     context: str = "", task_dispositions: dict[int, str] | None = None, expected_version: int) -> Handover:
    """Request a transfer (to a colleague) or a release (to a pool). Responsibility does not change yet."""
    if kind not in ("transfer", "release"):
        raise DomainError("Unknown handover type.", code="invalid_kind")
    if not reason.strip():
        raise DomainError("Give a reason for the handover.", code="reason_required")
    task_dispositions = task_dispositions or {}

    def run():
        assignment = Assignment.objects.select_related("user", "pool").get(contact=contact)
        if assignment.version != expected_version:
            raise ConflictError(f"Responsibility changed since you opened this page. Current: {assignment.describe()}.",
                                code="stale_assignment")
        if not can_initiate_handover(assignment, actor):
            raise NotAllowed("Only the current handler (or the pool coordinator for pool-held clients) can request a handover.")
        if kind == "transfer":
            if recipient is None or not recipient.is_active:
                raise DomainError("Choose an active colleague to receive the client.", code="invalid_recipient")
            if assignment.kind == "person" and recipient.pk == assignment.user_id:
                raise DomainError("This colleague is already responsible.", code="invalid_recipient")
        else:
            if assignment.kind != "person":
                raise DomainError("Only an individually assigned client can be released to a pool.", code="invalid_release")
            if pool is None or not pool.active:
                raise DomainError("Choose an active pool.", code="invalid_pool")
            if not pool.accountable_users():
                raise DomainError(
                    f"Pool '{pool}' has no active coordinator to accept releases. Configure one under Settings first.",
                    code="pool_accountability_gap",
                )
        open_tasks = list(Task.objects.filter(contact=contact, status="open"))
        missing = [t for t in open_tasks if t.pk not in task_dispositions]
        if missing:
            raise DomainError("Choose what happens to each open task before requesting the handover.",
                              code="task_disposition_required", details={"task_ids": [t.pk for t in missing]})
        now = clock.now()
        try:
            handover = Handover.objects.create(
                contact=contact, kind=kind, sender=actor if assignment.kind == "person" else actor,
                recipient=recipient if kind == "transfer" else None, pool=pool if kind == "release" else None,
                expected_version=expected_version, reason=reason.strip()[:300], context=context.strip(),
                requested_at=now, open_guard=contact.pk,
            )
        except IntegrityError as exc:
            raise ConflictError("Another handover for this client is already awaiting acceptance.", code="handover_open") from exc
        for task in open_tasks:
            disposition = task_dispositions[task.pk]
            if disposition not in ("keep", "transfer"):
                raise DomainError("Invalid task disposition.", code="invalid_disposition")
            HandoverTaskDisposition.objects.create(handover=handover, task=task, disposition=disposition)
        audit("handover.requested", handover, f"{handover.get_kind_display()} requested to {handover.destination_label()}",
              actor=actor, contact=contact, data={"reason": reason})
        emit("handover_requested", handover_id=handover.pk, event_key=f"handover:{handover.pk}")
        return handover

    return write_transaction(run)


def can_decide(handover: Handover, user) -> bool:
    if handover.kind == "transfer":
        return handover.recipient_id == user.pk
    return user in handover.pool.accountable_users()


def accept_handover(handover: Handover, *, actor) -> Handover:
    op_key = f"handover:{handover.pk}:accept"

    def run():
        h = Handover.objects.select_related("pool", "recipient", "contact").get(pk=handover.pk)
        if h.state == "accepted":
            if AssignmentEvent.objects.filter(operation_key=op_key).exists():
                return h  # idempotent replay: one logical transfer
        if not can_decide(h, actor):
            raise NotAllowed("Only the named recipient (or the destination pool's coordinator) can accept this handover.")
        if h.state != "requested":
            raise InvalidTransition(f"This handover is already {h.get_state_display().lower()}.")
        assignment = Assignment.objects.get(contact=h.contact)
        now = clock.now()
        if assignment.version != h.expected_version:
            Handover.objects.filter(pk=h.pk, state="requested").update(
                state="stale", decided_at=now, decided_by=actor, decision_note="Responsibility changed before acceptance",
                open_guard=None,
            )
            audit("handover.stale", h, "Acceptance refused: responsibility changed after the request", actor=actor, contact=h.contact)
            raise ConflictError("Responsibility changed after this request was made, so it can no longer be accepted.",
                                code="stale_handover")
        new_kind, new_user, new_pool = ("person", h.recipient, None) if h.kind == "transfer" else ("pool", None, h.pool)
        moved = Assignment.objects.filter(pk=assignment.pk, version=h.expected_version).update(
            kind=new_kind, user=new_user, pool=new_pool, since=now, version=F("version") + 1
        )
        if moved != 1:
            raise ConflictError("Responsibility changed while accepting. Nothing was transferred.", code="stale_handover")
        Handover.objects.filter(pk=h.pk).update(state="accepted", decided_at=now, decided_by=actor, open_guard=None)
        AssignmentEvent.objects.create(
            contact=h.contact, event_type="handover_accepted" if h.kind == "transfer" else "release_accepted",
            from_user=assignment.user, from_pool=assignment.pool, to_user=new_user, to_pool=new_pool, actor=actor,
            reason=h.reason, handover=h, operation_key=op_key, version_after=h.expected_version + 1, occurred_at=now,
        )
        # Apply explicit task dispositions. Tasks moved to a pool go to the coordinator who accepted.
        task_target = h.recipient if h.kind == "transfer" else actor
        for disp in h.task_dispositions.select_related("task"):
            if disp.disposition == "transfer" and disp.task.status == "open":
                Task.objects.filter(pk=disp.task_id, status="open").update(assignee=task_target, version=F("version") + 1)
                audit("task.reassigned", disp.task, f"Task reassigned to {task_target} by accepted handover",
                      actor=actor, contact=h.contact)
        audit("handover.accepted", h, f"{actor} accepted {h.get_kind_display().lower()}", actor=actor, contact=h.contact)
        emit("handover_closed", handover_id=h.pk, state="accepted", event_key=f"handover:{h.pk}:accepted")
        emit("assignment_changed", contact_id=h.contact_id, to_user_id=getattr(new_user, "pk", None),
             event_key=f"handover:{h.pk}:assignment")
        return Handover.objects.get(pk=h.pk)

    try:
        return write_transaction(run)
    except IntegrityError:
        if AssignmentEvent.objects.filter(operation_key=op_key).exists():
            return Handover.objects.get(pk=handover.pk)
        raise


def decline_handover(handover: Handover, *, actor, note: str) -> Handover:
    def run():
        h = Handover.objects.select_related("pool").get(pk=handover.pk)
        if not can_decide(h, actor):
            raise NotAllowed("Only the named recipient (or the destination pool's coordinator) can decline this handover.")
        if h.state != "requested":
            raise InvalidTransition(f"This handover is already {h.get_state_display().lower()}.")
        Handover.objects.filter(pk=h.pk, state="requested").update(
            state="declined", decided_at=clock.now(), decided_by=actor, decision_note=note.strip()[:300], open_guard=None
        )
        audit("handover.declined", h, f"{actor} declined; sender remains responsible", actor=actor, contact=h.contact,
              data={"note": note})
        emit("handover_closed", handover_id=h.pk, state="declined", event_key=f"handover:{h.pk}:declined")
        return Handover.objects.get(pk=h.pk)

    return write_transaction(run)


def cancel_handover(handover: Handover, *, actor, note: str = "") -> Handover:
    def run():
        h = Handover.objects.get(pk=handover.pk)
        if h.sender_id != actor.pk:
            raise NotAllowed("Only the person who requested this handover can cancel it.")
        if h.state != "requested":
            raise InvalidTransition(f"This handover is already {h.get_state_display().lower()}.")
        Handover.objects.filter(pk=h.pk, state="requested").update(
            state="cancelled", decided_at=clock.now(), decided_by=actor, decision_note=note.strip()[:300], open_guard=None
        )
        audit("handover.cancelled", h, "Handover cancelled by sender", actor=actor, contact=h.contact)
        emit("handover_closed", handover_id=h.pk, state="cancelled", event_key=f"handover:{h.pk}:cancelled")
        return Handover.objects.get(pk=h.pk)

    return write_transaction(run)


# --- Tasks -----------------------------------------------------------------------

def create_task(contact, *, actor, assignee, title: str, kind: str, due_at, description: str = "", critical: bool = False) -> Task:
    if not title.strip():
        raise DomainError("Give the task a title.", code="title_required")
    if assignee is None or not assignee.is_active:
        raise DomainError("Choose an active assignee.", code="invalid_assignee")
    if kind not in dict(Task.KINDS):
        raise DomainError("Unknown task type.", code="invalid_kind")

    def run():
        task = Task.objects.create(
            contact=contact, title=title.strip()[:200], kind=kind, description=description.strip(), assignee=assignee,
            created_by=actor, created_at=clock.now(), due_at=due_at, original_due_at=due_at, critical=critical,
        )
        audit("task.created", task, f"Task '{task.title}' for {assignee}", actor=actor, contact=contact)
        if assignee.pk != actor.pk:
            emit("task_assigned", task_id=task.pk, event_key=f"task-assigned:{task.pk}")
        return task

    return write_transaction(run)


def complete_task(task: Task, *, actor, note: str = "", expected_version: int) -> Task:
    def run():
        updated = Task.objects.filter(pk=task.pk, status="open", version=expected_version).update(
            status="done", completed_at=clock.now(), completed_by=actor, completion_note=note.strip()[:300],
            version=F("version") + 1,
        )
        if updated != 1:
            current = Task.objects.get(pk=task.pk)
            if current.status != "open":
                raise InvalidTransition(f"This task is already {current.get_status_display().lower()}.")
            raise ConflictError("This task was changed by someone else. Reload and try again.")
        fresh = Task.objects.get(pk=task.pk)
        audit("task.completed", fresh, f"Completed '{fresh.title}'", actor=actor, contact=fresh.contact, data={"note": note})
        emit("contact_activity", contact_id=fresh.contact_id, actor_id=actor.pk, task_id=fresh.pk)
        return fresh

    return write_transaction(run)


def replan_task(task: Task, *, actor, due_at, reason: str, expected_version: int) -> Task:
    if not reason.strip():
        raise DomainError("Give a reason for changing the due date.", code="reason_required")
    if due_at is None:
        raise DomainError("Choose a new due date.", code="due_required")

    def run():
        updated = Task.objects.filter(pk=task.pk, status="open", version=expected_version).update(
            due_at=due_at, replan_count=F("replan_count") + 1, last_replan_reason=reason.strip()[:200], version=F("version") + 1
        )
        if updated != 1:
            raise ConflictError("This task was changed or closed by someone else. Reload and try again.")
        fresh = Task.objects.get(pk=task.pk)
        audit("task.replanned", fresh, f"Due date changed: {reason}", actor=actor, contact=fresh.contact,
              data={"original_due_at": fresh.original_due_at.isoformat() if fresh.original_due_at else None,
                    "new_due_at": due_at.isoformat()})
        return fresh

    return write_transaction(run)


def reassign_task(task: Task, *, actor, assignee, expected_version: int) -> Task:
    if assignee is None or not assignee.is_active:
        raise DomainError("Choose an active assignee.", code="invalid_assignee")

    def run():
        updated = Task.objects.filter(pk=task.pk, status="open", version=expected_version).update(
            assignee=assignee, version=F("version") + 1
        )
        if updated != 1:
            raise ConflictError("This task was changed or closed by someone else. Reload and try again.")
        fresh = Task.objects.get(pk=task.pk)
        audit("task.reassigned", fresh, f"Task reassigned to {assignee}", actor=actor, contact=fresh.contact)
        emit("task_assigned", task_id=fresh.pk, event_key=f"task-assigned:{fresh.pk}:v{fresh.version}")
        return fresh

    return write_transaction(run)


def cancel_task(task: Task, *, actor, reason: str, expected_version: int) -> Task:
    if not reason.strip():
        raise DomainError("Give a reason for cancelling.", code="reason_required")

    def run():
        updated = Task.objects.filter(pk=task.pk, status="open", version=expected_version).update(
            status="cancelled", completion_note=reason.strip()[:300], completed_at=clock.now(), completed_by=actor,
            version=F("version") + 1,
        )
        if updated != 1:
            raise ConflictError("This task was changed or closed by someone else. Reload and try again.")
        fresh = Task.objects.get(pk=task.pk)
        audit("task.cancelled", fresh, f"Cancelled: {reason}", actor=actor, contact=fresh.contact)
        return fresh

    return write_transaction(run)
