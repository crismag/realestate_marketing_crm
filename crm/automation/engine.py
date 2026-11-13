"""Rule behaviour: event handlers, attention sweeps, digests and escalations (MOD-005).

Every handler re-reads current state before acting, routes to the CURRENT
responsible person, and creates notifications/messages under a logical key so
re-running a job or a sweep never duplicates a logical action.
"""
from __future__ import annotations

import datetime as dt
import zoneinfo

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from crm.attention import services as attention
from crm.contacts.models import Contact, Inquiry, Watch
from crm.core import clock
from crm.core.services import get_policy
from crm.work.models import Assignment, Handover, Task

from .models import DigestSnapshot, Notification, Rule, RuleRun
from .queue import enqueue

User = get_user_model()


def get_rule(key: str) -> Rule | None:
    return Rule.objects.filter(key=key).first()


def notify(*, recipients, kind: str, title: str, reason: str, logical_key: str, rule: Rule | None, body: str = "",
           contact=None, task=None, handover=None) -> tuple[int, int]:
    """Create one notification per recipient under ``logical_key``. Returns (created, gaps).

    With no recipients a single routing-gap record is stored instead, so the
    gap is visible rather than silently reported as delivered to nobody.
    """
    created = gaps = 0
    recipients = [u for u in dict.fromkeys(recipients) if u is not None and u.is_active]
    targets = recipients or [None]
    for user in targets:
        key = f"{logical_key}:u{user.pk}" if user else f"{logical_key}:gap"
        if Notification.objects.filter(logical_key=key).exists():
            continue
        try:
            with transaction.atomic():
                Notification.objects.create(
                    recipient=user, status="delivered" if user else "routing_gap", kind=kind, title=title[:200],
                    body=body, reason=reason[:300], contact=contact, task=task, handover=handover, rule=rule,
                    rule_version=getattr(rule, "version", None), logical_key=key, created_at=clock.now(),
                )
        except IntegrityError:
            continue
        if user:
            created += 1
        else:
            gaps += 1
    return created, gaps


def relationship_recipients(contact) -> list:
    assignment = Assignment.objects.select_related("user", "pool__coordinator", "pool__backup_coordinator").filter(
        contact=contact).first()
    if assignment is None:
        return []
    if assignment.kind == "person":
        return [assignment.user]
    return assignment.pool.accountable_users()


# --- Event handlers -------------------------------------------------------------

def on_inquiry_received(payload: dict) -> dict:
    inquiry = Inquiry.objects.select_related("contact").filter(pk=payload["inquiry_id"]).first()
    if inquiry is None:
        return {"skipped": "inquiry missing"}
    result = {}
    rule = get_rule("inquiry")
    if rule and rule.enabled and inquiry.status == "awaiting":
        created, gaps = notify(
            recipients=relationship_recipients(inquiry.contact), kind="inquiry",
            title=f"New inquiry from {inquiry.contact.display_name}",
            body=inquiry.message[:500], reason="You are responsible for this client (or coordinate its pool)",
            logical_key=f"inquiry:{inquiry.pk}", rule=rule, contact=inquiry.contact,
        )
        result["inquiry_alerts"] = created
        result["routing_gaps"] = gaps
    ack = get_rule("customer-followup")
    if ack and ack.enabled and inquiry.status == "awaiting" and inquiry.contact.email and not inquiry.contact.email_opt_out:
        from crm.comms.services import schedule_customer_message

        delay = int(ack.config.get("delay_minutes", 0))
        msg = schedule_customer_message(
            inquiry.contact, template_key=ack.config.get("template", "inquiry-ack"), rule=ack,
            logical_key=f"inquiry-ack:{inquiry.pk}", send_after=clock.now() + dt.timedelta(minutes=delay),
            context={"inquiry_id": inquiry.pk},
        )
        result["ack_scheduled"] = bool(msg)
    _notify_watchers(inquiry.contact, actor_id=None, what=f"New inquiry from {inquiry.contact.display_name}",
                     event_key=f"inquiry:{inquiry.pk}")
    return result


def on_became_client(payload: dict) -> dict:
    rule = get_rule("onboard")
    contact = Contact.objects.filter(pk=payload["contact_id"]).first()
    if not (rule and rule.enabled and contact):
        return {"skipped": "rule disabled or contact missing"}
    if not contact.email or contact.email_opt_out:
        return {"skipped": "no email or opted out"}
    from crm.comms.services import schedule_customer_message

    msg = schedule_customer_message(contact, template_key=rule.config.get("template", "onboarding"), rule=rule,
                                    logical_key=f"onboard:{contact.pk}")
    return {"onboarding_scheduled": bool(msg)}


def on_handover_requested(payload: dict) -> dict:
    h = Handover.objects.select_related("contact", "sender", "recipient", "pool").filter(pk=payload["handover_id"]).first()
    if h is None or h.state != "requested":
        return {"skipped": "handover no longer pending"}
    rule = get_rule("handover" if h.kind == "transfer" else "pool-release")
    if not (rule and rule.enabled):
        return {"skipped": "rule disabled"}
    deciders = [h.recipient] if h.kind == "transfer" else h.pool.accountable_users()
    created, gaps = notify(
        recipients=deciders, kind="handover_request",
        title=f"{h.sender} asks you to accept {h.contact.display_name}"
        if h.kind == "transfer" else f"Release of {h.contact.display_name} to {h.pool} needs your acceptance",
        body=f"Reason: {h.reason}\n{h.context}".strip(),
        reason="You are the named recipient" if h.kind == "transfer" else "You coordinate the destination pool",
        logical_key=f"handover:{h.pk}:request", rule=rule, contact=h.contact, handover=h,
    )
    return {"notified": created, "routing_gaps": gaps}


def on_handover_closed(payload: dict) -> dict:
    h = Handover.objects.select_related("contact", "sender", "decided_by").filter(pk=payload["handover_id"]).first()
    if h is None:
        return {"skipped": "missing"}
    rule = get_rule("handover" if h.kind == "transfer" else "pool-release")
    if not (rule and rule.enabled) or h.state not in ("accepted", "declined", "stale"):
        return {"skipped": "nothing to tell the sender"}
    created, _ = notify(
        recipients=[h.sender], kind="handover_outcome",
        title=f"Handover of {h.contact.display_name} {h.get_state_display().lower()}",
        body=h.decision_note,
        reason="You requested this handover" + (" and remain responsible" if h.state != "accepted" else ""),
        logical_key=f"handover:{h.pk}:{h.state}", rule=rule, contact=h.contact, handover=h,
    )
    return {"notified": created}


def on_task_assigned(payload: dict) -> dict:
    rule = get_rule("task-assigned")
    task = Task.objects.select_related("assignee", "contact", "created_by").filter(pk=payload["task_id"]).first()
    if not (rule and rule.enabled and task) or task.status != "open":
        return {"skipped": "rule disabled or task closed"}
    created, _ = notify(
        recipients=[task.assignee], kind="task_assigned", title=f"New task: {task.title}",
        body=f"For {task.contact.display_name}", reason="This task is assigned to you",
        logical_key=f"task-assigned:{task.pk}:v{task.version}:{task.assignee_id}", rule=rule, contact=task.contact, task=task,
    )
    return {"notified": created}


def _notify_watchers(contact, *, actor_id, what: str, event_key: str) -> int:
    rule = get_rule("watch")
    if not (rule and rule.enabled):
        return 0
    watchers = [w.user for w in Watch.objects.filter(contact=contact).select_related("user") if w.user_id != actor_id]
    if not watchers:
        return 0
    created, _ = notify(recipients=watchers, kind="watch", title=what, reason="You are watching this client",
                        logical_key=f"watch:{event_key}", rule=rule, contact=contact)
    return created


def on_contact_event(payload: dict, *, job_id: int) -> dict:
    contact = Contact.objects.filter(pk=payload["contact_id"]).first()
    if contact is None:
        return {"skipped": "missing"}
    what = f"Activity on {contact.display_name}"
    if payload.get("fields"):
        what = f"{contact.display_name} updated ({', '.join(payload['fields'])})"
    if payload.get("task_id"):
        what = f"Task completed for {contact.display_name}"
    return {"watch_alerts": _notify_watchers(contact, actor_id=payload.get("actor_id"), what=what, event_key=f"job{job_id}")}


def on_assignment_changed(payload: dict, *, job_id: int) -> dict:
    contact = Contact.objects.filter(pk=payload["contact_id"]).first()
    if contact is None:
        return {"skipped": "missing"}
    return {"watch_alerts": _notify_watchers(contact, actor_id=payload.get("to_user_id"),
                                             what=f"Responsibility changed for {contact.display_name}",
                                             event_key=f"job{job_id}")}


def on_customer_replied(payload: dict, *, job_id: int) -> dict:
    contact = Contact.objects.filter(pk=payload["contact_id"]).first()
    if contact is None:
        return {"skipped": "missing"}
    return {"watch_alerts": _notify_watchers(contact, actor_id=None, what=f"{contact.display_name} replied",
                                             event_key=f"job{job_id}")}


# --- Sweeps -----------------------------------------------------------------------

SWEEP_RULES = ("after-tour", "inactivity", "missing-next", "task-due", "handover", "pool-release", "escalation")


def planned_sweep_actions(now: dt.datetime, policy: dict) -> list[dict]:
    """Compute the notifications a sweep would create, without side effects (used by preview and sweep)."""
    items = attention.evaluate(now=now, policy=policy)
    rules = {r.key: r for r in Rule.objects.filter(key__in=SWEEP_RULES)}
    escalation_ids = policy["notifications"].get("escalation_recipient_ids") or []
    escalation_users = list(User.objects.filter(pk__in=escalation_ids, is_active=True))
    esc_hours = policy["attention"]["escalation_overdue_hours"]
    local_day = now.astimezone(zoneinfo.ZoneInfo(policy["timezone"])).date().isoformat()
    actions = []
    for item in items:
        c = item.contact
        for r in item.active_reasons:
            if r.code == "toured_no_followup":
                actions.append(dict(rule="after-tour", recipients=item.handler_users, contact=c,
                                    title=f"Follow up {c.display_name} after the tour", reason=r.detail,
                                    key=f"after-tour:{c.pk}:{r.since.isoformat()}", kind="attention"))
            elif r.code == "inactive":
                actions.append(dict(rule="inactivity", recipients=item.handler_users, contact=c,
                                    title=f"{c.display_name} has gone quiet", reason=r.detail,
                                    key=f"inactivity:{c.pk}:{r.since.isoformat()}", kind="attention"))
            elif r.code == "next_action_missing":
                anchor = Task.objects.filter(contact=c).exclude(status="open").order_by("-completed_at").values_list(
                    "completed_at", flat=True).first() or c.created_at
                actions.append(dict(rule="missing-next", recipients=item.handler_users, contact=c,
                                    title=f"Plan the next step for {c.display_name}", reason=r.detail,
                                    key=f"missing-next:{c.pk}:{anchor.isoformat()}", kind="attention"))
            elif r.code in ("task_overdue", "promise_due"):
                t = r.task
                actions.append(dict(rule="task-due", recipients=[t.assignee], contact=c, task=t,
                                    title=f"Overdue: {t.title}", reason=r.detail,
                                    key=f"task-due:{t.pk}:{t.due_at.isoformat()}", kind="task_due"))
                if now - t.due_at > dt.timedelta(hours=esc_hours):
                    actions.append(dict(rule="escalation", recipients=escalation_users, contact=c, task=t,
                                        title=f"Escalation: '{t.title}' overdue for {c.display_name}",
                                        reason=f"Overdue more than {esc_hours} h; {t.assignee} remains assignee",
                                        key=f"escalation:{t.pk}:{t.due_at.isoformat()}", kind="escalation"))
            elif r.code == "handover_waiting" and r.overdue:
                h = r.handover
                rule_key = "handover" if h.kind == "transfer" else "pool-release"
                deciders = [h.recipient] if h.kind == "transfer" else h.pool.accountable_users()
                actions.append(dict(rule=rule_key, recipients=deciders, contact=c, handover=h,
                                    title=f"Still waiting: accept {c.display_name}?", reason=r.detail,
                                    key=f"handover:{h.pk}:pending:{local_day}", kind="handover_request"))
                actions.append(dict(rule=rule_key, recipients=[h.sender], contact=c, handover=h,
                                    title=f"You are still responsible for {c.display_name}",
                                    reason="Your handover has not been accepted yet (ADR-001)",
                                    key=f"handover:{h.pk}:sender:{local_day}", kind="accountability"))
    for action in actions:
        action["rule_obj"] = rules.get(action["rule"])
        keys = [f"{action['key']}:u{u.pk}" for u in action["recipients"] if u and u.is_active] or [f"{action['key']}:gap"]
        action["already_sent"] = Notification.objects.filter(logical_key__in=keys).count() == len(keys)
    return actions


def run_sweep(now: dt.datetime | None = None, *, job=None) -> dict:
    now = now or clock.now()
    policy = get_policy()
    actions = planned_sweep_actions(now, policy)
    runs: dict[str, RuleRun] = {}
    totals = {"created": 0, "gaps": 0, "skipped_disabled": 0}
    for rule in Rule.objects.filter(key__in=SWEEP_RULES, enabled=True):
        runs[rule.key] = RuleRun.objects.create(rule=rule, rule_version=rule.version, evaluated_for=now, job=job,
                                                started_at=clock.now())
    for action in actions:
        rule = action["rule_obj"]
        if rule is None or not rule.enabled:
            totals["skipped_disabled"] += 1
            continue
        run = runs[rule.key]
        run.matched += 1
        if action["already_sent"]:
            run.suppressed += 1
            continue
        created, gaps = notify(recipients=action["recipients"], kind=action["kind"], title=action["title"],
                               reason=action["reason"], logical_key=action["key"], rule=rule, contact=action["contact"],
                               task=action.get("task"), handover=action.get("handover"))
        run.created += created
        totals["created"] += created
        totals["gaps"] += gaps
    for run in runs.values():
        run.outcome = "succeeded"
        run.finished_at = clock.now()
        run.save()
    return totals


def run_digest(now: dt.datetime | None = None, *, job=None) -> dict:
    """One digest per active user per local day; recipients and counts evaluated now."""
    now = now or clock.now()
    rule = get_rule("digest")
    if not (rule and rule.enabled):
        return {"skipped": "digest disabled"}
    policy = get_policy()
    local_day = now.astimezone(zoneinfo.ZoneInfo(policy["timezone"])).date()
    run = RuleRun.objects.create(rule=rule, rule_version=rule.version, evaluated_for=now, job=job, started_at=clock.now())
    items = attention.evaluate(now=now, policy=policy)
    for user in User.objects.filter(is_active=True):
        mine = attention.filter_items(items, user=user, scope="mine")
        current_ids = {item.contact.pk for item in mine}
        logical_key = f"digest:{user.pk}:{local_day.isoformat()}"
        # Commit the comparison baseline together with the delivered notification.
        # Daily replay must not replace the original snapshot with later state.
        with transaction.atomic():
            if Notification.objects.filter(logical_key=f"{logical_key}:u{user.pk}").exists():
                run.suppressed += 1
                continue
            previous = DigestSnapshot.objects.filter(recipient=user, day__lt=local_day).first()
            previous_ids = set(previous.contact_ids) if previous else set()
            new = len(current_ids - previous_ids)
            continuing = len(current_ids & previous_ids)
            resolved = len(previous_ids - current_ids)
            if not current_ids and not resolved:
                continue
            run.matched += 1
            summary = attention.summarize(mine)
            lines = [f"{attention.REASONS[c]}: {n}" for c, n in summary["per_reason"].items() if n]
            comparison = (f"Compared with your previous delivered digest ({previous.day.isoformat()})."
                          if previous else "No previous delivered digest; all current clients count as new.")
            created, _ = notify(
                recipients=[user], kind="digest",
                title=f"Daily digest: {len(current_ids)} client(s) need attention "
                      f"({new} new, {continuing} continuing, {resolved} resolved)",
                body="\n".join(lines) + "\nReason counts overlap; the client total counts each client once.\n"
                     + comparison + " Resolved means no longer in your attention queue.",
                reason="Daily attention digest", logical_key=logical_key, rule=rule,
            )
            if created:
                email_on = bool(policy.get("notifications", {}).get("digest_email", True))
                snapshot = DigestSnapshot.objects.create(
                    recipient=user, day=local_day, contact_ids=sorted(current_ids),
                    notification=Notification.objects.get(logical_key=f"{logical_key}:u{user.pk}"),
                    created_at=now,
                    email_state="queued" if email_on else "skipped",
                    email_note="" if email_on else "Staff digest email is off.",
                )
                if email_on:
                    enqueue(
                        "staff.digest_email", {"snapshot_id": snapshot.pk},
                        logical_key=f"staff-digest:{user.pk}:{local_day.isoformat()}",
                        max_attempts=4, rule=rule,
                    )
            run.created += created
            run.suppressed += 0 if created else 1
    run.outcome = "succeeded"
    run.finished_at = clock.now()
    run.save()
    return {"digests": run.created}


def deliver_staff_digest(job) -> dict:
    """Prepare one staff-only copy of a digest. Never a customer message.

    The mail call stays outside the database transaction. A copy already filed,
    handed to staff mail, or skipped is not prepared again.
    """
    from django.conf import settings
    from django.core.mail import send_mail

    from crm.core.db import write_transaction
    from crm.core.services import audit

    snapshot = (
        DigestSnapshot.objects.select_related("recipient", "notification")
        .filter(pk=(job.payload or {}).get("snapshot_id"))
        .first()
    )
    if snapshot is None:
        return {"status": "missing"}
    if snapshot.email_state in ("filed", "smtp", "skipped"):
        return {"status": snapshot.email_state}

    user = snapshot.recipient
    note = snapshot.notification

    def mark(state: str, detail: str) -> None:
        def write():
            updated = DigestSnapshot.objects.filter(pk=snapshot.pk).exclude(
                email_state__in=("filed", "smtp", "skipped"),
            ).update(email_state=state, email_note=detail[:200])
            if not updated:
                return
            if state in ("filed", "smtp"):
                audit(
                    "staff.digest_emailed", snapshot,
                    "Staff digest copy prepared. Not a customer message.",
                    data={"state": state, "recipient_id": user.pk, "day": snapshot.day.isoformat()},
                )
            elif state == "skipped":
                audit(
                    "staff.digest_email_skipped", snapshot, detail[:300],
                    data={"recipient_id": user.pk, "day": snapshot.day.isoformat()},
                )

        write_transaction(write)

    if not bool(get_policy().get("notifications", {}).get("digest_email", True)):
        mark("skipped", "Staff digest email is off.")
        return {"status": "skipped"}
    if not user.is_active or not user.email:
        mark("skipped", "No active staff email address.")
        return {"status": "skipped"}

    via_smtp = settings.EMAIL_BACKEND.endswith("smtp.EmailBackend")
    subject = f"[Staff] {note.title} — not a customer message"
    body = (
        "This message is for staff only. It was not sent to a customer.\n"
        "Reading it does not complete the underlying work.\n\n"
        f"{note.title}\n\n{note.body}\n"
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    if via_smtp:
        mark("smtp", "Handed to the configured staff mail server. Not a customer message.")
        return {"status": "smtp"}
    mark("filed", "Written to the staff mail folder. Not a customer message.")
    return {"status": "filed"}
