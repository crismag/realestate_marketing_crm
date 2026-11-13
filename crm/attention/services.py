"""Derived attention: which relationships need someone, why, and since when (REQ-016, REQ-026).

Attention is always computed from source facts at evaluation time, never stored
as a flag that could drift. Each reason carries its own timestamp and the
recipient it routes to. Several reasons can apply to one contact; unique
contact totals are counted separately from reason totals.
"""
from __future__ import annotations

import datetime as dt
import zoneinfo
from collections import defaultdict
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from crm.accounts.models import User
from crm.contacts.models import Contact, Inquiry, Interaction, Opportunity
from crm.core import clock
from crm.core.errors import DomainError
from crm.core.services import audit
from crm.work.models import Handover, Task

from .models import Snooze

REASONS = {
    "inquiry_awaiting": "Customer awaiting response",
    "toured_no_followup": "Toured, no follow-up recorded",
    "task_overdue": "Task overdue",
    "promise_due": "Promise to customer due",
    "inactive": "Inactive relationship",
    "next_action_missing": "Next action missing",
    "opportunity_stalled": "Opportunity stalled",
    "pool_waiting": "Waiting in shared pool",
    "handover_waiting": "Handover awaiting acceptance",
    "critical_task": "Critical task open",
    "handler_inactive": "Responsible colleague deactivated",
}
REASON_ORDER = list(REASONS)
SNOOZABLE = {"toured_no_followup", "inactive", "next_action_missing", "opportunity_stalled", "pool_waiting"}
SEVERE = {"handler_inactive", "inquiry_awaiting", "task_overdue", "promise_due", "handover_waiting", "critical_task"}


@dataclass
class Reason:
    code: str
    since: dt.datetime | None
    detail: str
    recipients: list = field(default_factory=list)  # users this reason routes to
    task: Task | None = None
    handover: Handover | None = None
    inquiry: Inquiry | None = None
    overdue: bool = False
    snoozed_until: dt.datetime | None = None

    @property
    def label(self) -> str:
        return REASONS[self.code]

    @property
    def snoozable(self) -> bool:
        return self.code in SNOOZABLE


@dataclass
class AttentionItem:
    contact: Contact
    handler_label: str
    handler_users: list
    reasons: list[Reason]
    last_attempt: dt.datetime | None
    last_success: dt.datetime | None
    last_tour: dt.datetime | None
    next_task: Task | None

    @property
    def active_reasons(self) -> list[Reason]:
        return [r for r in self.reasons if r.snoozed_until is None]

    @property
    def snoozed_reasons(self) -> list[Reason]:
        return [r for r in self.reasons if r.snoozed_until is not None]

    @property
    def oldest_since(self) -> dt.datetime | None:
        times = [r.since for r in self.active_reasons if r.since]
        return min(times) if times else None

    @property
    def severity(self) -> int:
        return 0 if any(r.code in SEVERE for r in self.active_reasons) else 1


def _handler(contact) -> tuple[str, list]:
    assignment = getattr(contact, "assignment", None)
    if assignment is None:
        return "No responsibility recorded", []
    if assignment.kind == "person":
        return str(assignment.user), [assignment.user]
    users = assignment.pool.accountable_users()
    label = f"Pool: {assignment.pool}" + (f" (coordinator {users[0]})" if users else " (no coordinator)")
    return label, users


def evaluate(*, now: dt.datetime | None = None, policy: dict, contact_ids: list[int] | None = None) -> list[AttentionItem]:
    now = now or clock.now()
    ap = policy["attention"]
    contacts = Contact.objects.filter(archived_at__isnull=True).select_related(
        "assignment__user", "assignment__pool__coordinator", "assignment__pool__backup_coordinator"
    )
    if contact_ids is not None:
        contacts = contacts.filter(pk__in=contact_ids)
    contacts = list(contacts)
    ids = [c.pk for c in contacts]
    if not ids:
        return []

    kind_max: dict[int, dict[str, dt.datetime]] = defaultdict(dict)
    for row in (
        Interaction.objects.filter(contact_id__in=ids, occurred_at__lte=now)
        .values("contact_id", "kind").annotate(last=Max("occurred_at"))
    ):
        kind_max[row["contact_id"]][row["kind"]] = row["last"]

    inquiries = defaultdict(list)
    for inq in Inquiry.objects.filter(contact_id__in=ids, status="awaiting").order_by("received_at"):
        inquiries[inq.contact_id].append(inq)

    tasks = defaultdict(list)
    for task in Task.objects.filter(contact_id__in=ids, status="open").select_related("assignee").order_by("due_at"):
        tasks[task.contact_id].append(task)

    opportunities = defaultdict(list)
    for opp in Opportunity.objects.filter(contact_id__in=ids, outcome="open").order_by("created_at"):
        opportunities[opp.contact_id].append(opp)
    local_today = timezone.localtime(now, zoneinfo.ZoneInfo(policy["timezone"])).date()

    handovers = {}
    for h in Handover.objects.filter(contact_id__in=ids, state="requested").select_related(
        "sender", "recipient", "pool__coordinator", "pool__backup_coordinator"
    ):
        handovers[h.contact_id] = h

    snoozes = defaultdict(dict)
    for s in Snooze.objects.filter(contact_id__in=ids, until__gt=now, cleared_at__isnull=True):
        current = snoozes[s.contact_id].get(s.reason_code)
        if current is None or s.until > current:
            snoozes[s.contact_id][s.reason_code] = s.until

    followup_types = set(ap["followup_types"]) - {"meeting_tour"}
    reset_types = set(ap["contact_reset_types"])
    items: list[AttentionItem] = []
    admins = None  # loaded only if a deactivated colleague still holds a client
    for contact in contacts:
        kinds = kind_max.get(contact.pk, {})
        handler_label, handler_users = _handler(contact)
        last_attempt = kinds.get("outbound_attempt")
        success = [kinds[k] for k in ("conversation", "inbound_reply", "meeting_tour") if k in kinds]
        last_success = max(success) if success else None
        last_tour = kinds.get("meeting_tour")
        resets = [kinds[k] for k in reset_types if k in kinds]
        last_reset = max(resets) if resets else None
        open_tasks = tasks.get(contact.pk, [])
        future_tasks = [t for t in open_tasks if t.due_at is not None and t.due_at >= now]
        dated_tasks = [t for t in open_tasks if t.due_at is not None]
        next_task = dated_tasks[0] if dated_tasks else (open_tasks[0] if open_tasks else None)
        relationship_active = contact.disposition in ("active", "nurture")
        agreed_later = contact.next_contact_agreed_at is not None and contact.next_contact_agreed_at > now
        reasons: list[Reason] = []

        for inq in inquiries.get(contact.pk, []):
            hours = (now - inq.received_at).total_seconds() / 3600
            reasons.append(Reason(
                "inquiry_awaiting", inq.received_at,
                f"Inquiry via {inq.get_channel_display().lower()} received {_ago(now, inq.received_at)}",
                handler_users, inquiry=inq, overdue=hours > ap["inquiry_response_hours"],
            ))

        if relationship_active and last_tour is not None:
            followup = [kinds[k] for k in followup_types if k in kinds and kinds[k] > last_tour]
            if not followup and now - last_tour > dt.timedelta(hours=ap["after_tour_hours"]):
                reasons.append(Reason("toured_no_followup", last_tour,
                                      f"Tour {_ago(now, last_tour)} with no follow-up recorded since", handler_users))

        for task in open_tasks:
            if task.due_at is not None and task.due_at < now:
                code = "promise_due" if task.kind == "promise" else "task_overdue"
                reasons.append(Reason(code, task.due_at, f"'{task.title}' was due {_ago(now, task.due_at)} ({task.assignee})",
                                      [task.assignee], task=task, overdue=True))
            elif task.critical:
                reasons.append(Reason("critical_task", task.created_at, f"Critical: '{task.title}' ({task.assignee})",
                                      [task.assignee], task=task))

        if relationship_active and contact.disposition == "active" and not agreed_later:
            limit_days = ap["inactivity_days"].get(contact.lifecycle)
            if limit_days:
                anchor = last_reset or contact.created_at
                if now - anchor > dt.timedelta(days=limit_days):
                    detail = (f"Last recorded contact {_ago(now, last_reset)}" if last_reset
                              else f"No contact recorded since capture {_ago(now, contact.created_at)}")
                    reasons.append(Reason("inactive", anchor, f"{detail}; cadence {limit_days} days", handler_users))

        if (relationship_active and contact.lifecycle in ap["missing_next_action_lifecycles"]
                and not future_tasks and not agreed_later and not any(t.due_at is None for t in open_tasks)):
            if not any(r.code in ("task_overdue", "promise_due") for r in reasons):
                reasons.append(Reason("next_action_missing", None, "No open follow-up task or agreed contact date", handler_users))

        if relationship_active:
            # One reason per contact covering every stalled opportunity, so a snooze (keyed by contact and
            # reason) covers exactly what the person saw rather than hiding a reminder they never saw.
            stalled = [(opp, s) for opp in opportunities.get(contact.pk, [])
                       if (s := _stalled(opp, now=now, today=local_today, ap=ap))]
            if stalled:
                reasons.append(Reason("opportunity_stalled", min(s[0] for _, s in stalled),
                                      "; ".join(f"'{opp.title}': {s[1]}" for opp, s in stalled), handler_users))

        assignment = getattr(contact, "assignment", None)
        if assignment is not None and assignment.kind == "person" and not assignment.user.is_active:
            if admins is None:
                admins = list(User.objects.filter(is_active=True, is_staff=True))
            reasons.append(Reason("handler_inactive", None,
                                  f"{assignment.user} is deactivated; an administrator should hand this client over",
                                  admins, overdue=True))

        if assignment is not None and assignment.kind == "pool":
            reasons.append(Reason("pool_waiting", assignment.since,
                                  f"In pool {assignment.pool} since {_ago(now, assignment.since)}", handler_users,
                                  overdue=now - assignment.since > dt.timedelta(hours=ap["pool_waiting_hours"])))

        handover = handovers.get(contact.pk)
        if handover is not None:
            deciders = [handover.recipient] if handover.kind == "transfer" else handover.pool.accountable_users()
            waited = now - handover.requested_at
            reasons.append(Reason(
                "handover_waiting", handover.requested_at,
                f"{handover.get_kind_display()} to {handover.destination_label()} requested {_ago(now, handover.requested_at)}; "
                f"{handover.sender} stays responsible until accepted",
                [u for u in deciders if u] + [handover.sender], handover=handover,
                overdue=waited > dt.timedelta(hours=ap["handover_pending_hours"]),
            ))

        for reason in reasons:
            if reason.code in SNOOZABLE and reason.code in snoozes.get(contact.pk, {}):
                reason.snoozed_until = snoozes[contact.pk][reason.code]
        if reasons:
            reasons.sort(key=lambda r: REASON_ORDER.index(r.code))
            items.append(AttentionItem(contact, handler_label, handler_users, reasons, last_attempt, last_success,
                                       last_tour, next_task))
    items.sort(key=lambda i: (i.severity, i.oldest_since or now, i.contact.display_name))
    return items


def _stalled(opp: Opportunity, *, now: dt.datetime, today: dt.date, ap: dict) -> tuple[dt.datetime, str] | None:
    """Open opportunity whose stage has not moved in N days, or whose expected close date has passed (C-R2).

    Uses `stage_changed_at`, which only moves when the stage really changes, so editing the amount or
    title does not reset the clock. Both checks are implementation defaults; 0 / false switch them off.
    """
    days = ap.get("stalled_opportunity_days", 0)
    changed = opp.stage_changed_at or opp.created_at
    if ap.get("flag_past_expected_close", False) and opp.expected_close and opp.expected_close < today:
        since = dt.datetime.combine(opp.expected_close, dt.time.min, tzinfo=dt.UTC)
        return since, f"expected close {opp.expected_close:%Y-%m-%d} has passed and it is still open"
    if days and now - changed > dt.timedelta(days=days):
        return changed, f"stage unchanged since {_ago(now, changed)} (limit {days} days)"
    return None


def _ago(now: dt.datetime, then: dt.datetime | None) -> str:
    if then is None:
        return "never"
    seconds = (now - then).total_seconds()
    if seconds < 0:
        return "in the future"
    if seconds < 3600:
        return f"{int(seconds // 60)} min ago"
    if seconds < 86400 * 2:
        return f"{int(seconds // 3600)} h ago"
    return f"{int(seconds // 86400)} days ago"


def filter_items(items: list[AttentionItem], *, user=None, scope: str = "mine", reason: str = "",
                 include_snoozed: bool = False, pool_id: int | None = None, team_id: int | None = None) -> list[AttentionItem]:
    result = []
    for item in items:
        reasons = item.reasons if include_snoozed else item.active_reasons
        if reason:
            reasons = [r for r in reasons if r.code == reason]
        if scope == "mine" and user is not None:
            reasons = [r for r in reasons if user in r.recipients or user in item.handler_users]
        if pool_id:
            assignment = getattr(item.contact, "assignment", None)
            if not (assignment and assignment.pool_id == pool_id):
                continue
        if team_id:
            if not any(team_id in [t.pk for t in u.teams.all()] for u in item.handler_users):
                continue
        if reasons:
            result.append(AttentionItem(item.contact, item.handler_label, item.handler_users, reasons,
                                        item.last_attempt, item.last_success, item.last_tour, item.next_task))
    return result


def summarize(items: list[AttentionItem]) -> dict:
    """Unique-contact total plus per-reason counts (which overlap and must not be summed)."""
    per_reason = {code: 0 for code in REASONS}
    for item in items:
        for code in {r.code for r in item.active_reasons}:
            per_reason[code] += 1
    unique = sum(1 for item in items if item.active_reasons)
    return {"unique_contacts": unique, "per_reason": per_reason}


def snooze(contact: Contact, *, actor, reason_code: str, until: dt.datetime, note: str) -> Snooze:
    if reason_code not in SNOOZABLE:
        raise DomainError("This attention reason cannot be snoozed; act on it or replan the task instead.", code="not_snoozable")
    if not note.strip():
        raise DomainError("Say why you are snoozing this.", code="note_required")
    if until <= clock.now():
        raise DomainError("Snooze until a future time.", code="invalid_until")
    if until - clock.now() > dt.timedelta(days=180):
        raise DomainError("Snooze for at most 180 days.", code="invalid_until")
    with transaction.atomic():
        obj = Snooze.objects.create(contact=contact, reason_code=reason_code, until=until, note=note.strip()[:300],
                                    created_by=actor, created_at=clock.now())
        audit("attention.snoozed", obj, f"Snoozed '{REASONS[reason_code]}' until {until:%Y-%m-%d %H:%M} UTC: {note}",
              actor=actor, contact=contact)
        return obj


def clear_snooze(contact: Contact, *, actor, reason_code: str) -> int:
    with transaction.atomic():
        count = Snooze.objects.filter(contact=contact, reason_code=reason_code, cleared_at__isnull=True,
                                      until__gt=clock.now()).update(cleared_at=clock.now())
        if count:
            audit("attention.unsnoozed", contact, f"Snooze cleared for '{REASONS[reason_code]}'", actor=actor, contact=contact)
        return count


def coverage(*, now: dt.datetime, policy: dict, user=None) -> dict:
    """Follow-up coverage: eligible relationships whose last qualifying contact is within cadence.

    Eligible = not archived, disposition active, lifecycle has a cadence, and (if
    a user is given) currently handled by that user. Zero denominator = not applicable.
    """
    ap = policy["attention"]
    qs = Contact.objects.filter(archived_at__isnull=True, disposition="active",
                                lifecycle__in=[k for k, v in ap["inactivity_days"].items() if v])
    if user is not None:
        qs = qs.filter(assignment__kind="person", assignment__user=user)
    contacts = list(qs.only("id", "lifecycle", "created_at", "next_contact_agreed_at"))
    last = {
        r["contact_id"]: r["last"]
        for r in Interaction.objects.filter(contact__in=contacts, kind__in=ap["contact_reset_types"], occurred_at__lte=now)
        .values("contact_id").annotate(last=Max("occurred_at"))
    }
    met, missing_history, met_ids, unmet_ids = 0, 0, [], []
    for c in contacts:
        cadence = dt.timedelta(days=ap["inactivity_days"][c.lifecycle])
        last_contact = last.get(c.pk)
        if last_contact is None:
            missing_history += 1
        ok = (last_contact is not None and now - last_contact <= cadence) or (
            c.next_contact_agreed_at is not None and c.next_contact_agreed_at > now)
        if ok:
            met += 1
            met_ids.append(c.pk)
        else:
            unmet_ids.append(c.pk)
    total = len(contacts)
    return {
        "eligible": total,
        "met": met,
        "ratio": (met / total) if total else None,
        "missing_history": missing_history,
        "met_ids": met_ids,
        "unmet_ids": unmet_ids,
    }


def open_task_q(now):
    return Q(status="open", due_at__lt=now)
