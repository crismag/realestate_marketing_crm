"""Customer-facing messages: scheduling, stop-policy recheck and transport (MOD-006)."""
from __future__ import annotations

import datetime as dt
import re
import zoneinfo

from django.db import IntegrityError, transaction

from crm.automation.queue import enqueue
from crm.contacts.models import Contact, Inquiry, Interaction
from crm.core import clock
from crm.core.services import audit, get_policy

from .models import MessageTemplate, OutboundMessage
from .transports import TransportError, TransportTimeout, get_transport

PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


def render_template(text: str, values: dict) -> str:
    """Substitute only whitelisted placeholders; unknown ones are left visible. Output is plain text."""
    return PLACEHOLDER.sub(lambda m: str(values.get(m.group(1), m.group(0))), text)


def template_values(contact: Contact, policy: dict) -> dict:
    assignment = getattr(contact, "assignment", None)
    if assignment is not None and assignment.kind == "person":
        handler = assignment.user.full_name
    else:
        handler = "Our team"
    return {"customer_name": contact.display_name, "handler_name": handler, **company_values(policy)}


def company_values(policy: dict) -> dict:
    company = policy.get("company") or {}
    return {"workspace_name": policy["workspace_name"],
            **{f"company_{k}": company.get(k, "") for k in ("phone", "email", "website", "address")}}


def adjust_for_quiet_hours(moment: dt.datetime, policy: dict) -> dt.datetime:
    n = policy["notifications"]
    start, end = int(n["quiet_hours_start"]), int(n["quiet_hours_end"])
    if start == end:
        return moment
    tz = zoneinfo.ZoneInfo(policy["timezone"])
    local = moment.astimezone(tz)
    hour = local.hour
    in_quiet = (hour >= start or hour < end) if start > end else (start <= hour < end)
    if not in_quiet:
        return moment
    target = local.replace(hour=end, minute=0, second=0, microsecond=0)
    if target <= local:
        target += dt.timedelta(days=1)
    return target.astimezone(dt.UTC)


def schedule_customer_message(contact: Contact, *, template_key: str, rule, logical_key: str,
                              send_after: dt.datetime | None = None, context: dict | None = None) -> OutboundMessage | None:
    """Create one logical customer message (deduplicated by logical_key) and its send job."""
    policy = get_policy()
    template = MessageTemplate.objects.filter(key=template_key).first()
    when = adjust_for_quiet_hours(send_after or clock.now(), policy)
    try:
        with transaction.atomic():
            msg = OutboundMessage.objects.create(
                contact=contact, template=template, template_version=getattr(template, "version", None),
                rule=rule, rule_version=getattr(rule, "version", None), to_address=contact.email,
                logical_key=logical_key, status="scheduled", transport="sandbox", scheduled_for=when,
                status_reason="", created_at=clock.now(),
            )
            if context:
                msg.status_reason = ""
            enqueue("comms.send", {"message_id": msg.pk, **(context or {})}, logical_key=f"send:{msg.pk}", run_at=when,
                    max_attempts=4, rule=rule)
            return msg
    except IntegrityError:
        return None


def _stop_reason(msg: OutboundMessage, payload: dict, policy: dict) -> str | None:
    contact = Contact.objects.get(pk=msg.contact_id)
    rule = msg.rule
    if rule is not None and not rule.enabled:
        return "cancelled:Rule was disabled before sending (queued messages are cancelled)"
    if msg.template is None or not msg.template.active:
        return "suppressed:Template missing or inactive"
    if contact.archived_at is not None:
        return "suppressed:Contact archived"
    if contact.email_opt_out:
        return "suppressed:Customer opted out of email"
    if not contact.email:
        return "suppressed:No email address on file"
    inquiry_id = payload.get("inquiry_id")
    if inquiry_id:
        inquiry = Inquiry.objects.filter(pk=inquiry_id).first()
        if inquiry is None or inquiry.status != "awaiting":
            return "suppressed:Inquiry already answered or closed by a person"
        if Interaction.objects.filter(contact=contact, kind="inbound_reply", occurred_at__gte=inquiry.received_at).exists():
            return "suppressed:Customer replied before the message was sent"
    cap = dt.timedelta(hours=policy["notifications"]["customer_frequency_cap_hours"])
    recent = OutboundMessage.objects.filter(
        contact=contact, status__in=("sandbox_captured", "delivered", "uncertain"), attempted_at__gt=clock.now() - cap
    ).exclude(pk=msg.pk)
    if recent.exists():
        return "suppressed:Frequency cap (another automated message was sent recently)"
    return None


class RetryLater(Exception):
    def __init__(self, message: str, run_at: dt.datetime | None = None):
        super().__init__(message)
        self.run_at = run_at


def send_message(message_id: int, payload: dict) -> dict:
    """Job handler. Rechecks current state immediately before sending."""
    policy = get_policy()
    msg = OutboundMessage.objects.select_related("template", "rule", "contact").get(pk=message_id)
    if msg.status != "scheduled":
        return {"skipped": f"status is {msg.status}"}
    stop = _stop_reason(msg, payload, policy)
    if stop:
        status, reason = stop.split(":", 1)
        OutboundMessage.objects.filter(pk=msg.pk, status="scheduled").update(status=status, status_reason=reason)
        audit("message." + status, msg, f"Customer message {status}: {reason}", actor_kind="worker", contact=msg.contact)
        return {"status": status, "reason": reason}
    now = clock.now()
    deferred = adjust_for_quiet_hours(now, policy)
    if deferred > now:
        raise RetryLater("Quiet hours: deferred", run_at=deferred)
    values = template_values(msg.contact, policy)
    subject = render_template(msg.template.subject, values)
    body = render_template(msg.template.body, values)
    # Mark the attempt before talking to the transport so a crash leaves evidence.
    OutboundMessage.objects.filter(pk=msg.pk).update(
        subject=subject, body=body, to_address=msg.contact.email, attempted_at=now,
        template_version=msg.template.version,
    )
    transport = get_transport()
    try:
        ref = transport.send(message_id=msg.pk, to=msg.contact.email, subject=subject, body=body)
    except TransportTimeout as exc:
        OutboundMessage.objects.filter(pk=msg.pk).update(status="uncertain", status_reason=str(exc)[:300])
        audit("message.uncertain", msg, "Delivery outcome unknown; not retried automatically to avoid duplicates",
              actor_kind="worker", contact=msg.contact)
        return {"status": "uncertain"}
    except TransportError as exc:
        OutboundMessage.objects.filter(pk=msg.pk).update(status_reason=f"Attempt failed: {exc}"[:300])
        raise
    OutboundMessage.objects.filter(pk=msg.pk).update(status=transport.final_status, provider_ref=ref,
                                                     status_reason="Stored locally by the sandbox transport; nothing was sent")
    audit("message.captured", msg, f"Customer message captured by {transport.name} transport (not sent)",
          actor_kind="worker", contact=msg.contact)
    return {"status": transport.final_status, "ref": ref}


def mark_failed(message_id: int, error: str) -> None:
    OutboundMessage.objects.filter(pk=message_id, status="scheduled").update(status="failed", status_reason=error[:300])


def retry_message(msg: OutboundMessage, *, actor) -> OutboundMessage:
    """Controlled manual retry for failed (not uncertain) messages."""
    from crm.core.errors import DomainError

    if msg.status != "failed":
        raise DomainError("Only failed messages can be retried. Uncertain deliveries need manual review.", code="not_retryable")
    with transaction.atomic():
        OutboundMessage.objects.filter(pk=msg.pk, status="failed").update(status="scheduled", status_reason="Manual retry requested")
        enqueue("comms.send", {"message_id": msg.pk}, logical_key=f"send:{msg.pk}:retry:{clock.now().timestamp():.0f}",
                max_attempts=1, rule=msg.rule)
        audit("message.retry", msg, "Manual retry of failed customer message", actor=actor, contact=msg.contact)
    return OutboundMessage.objects.get(pk=msg.pk)


def resolve_uncertain(msg: OutboundMessage, *, actor, outcome: str, note: str) -> OutboundMessage:
    from crm.core.errors import DomainError

    if msg.status != "uncertain":
        raise DomainError("Only uncertain messages can be resolved.", code="not_uncertain")
    if outcome not in ("failed", "cancelled"):
        raise DomainError("Unknown outcome.", code="invalid_outcome")
    if not note.strip():
        raise DomainError("Record what you checked.", code="note_required")
    with transaction.atomic():
        OutboundMessage.objects.filter(pk=msg.pk, status="uncertain").update(status=outcome, status_reason=note.strip()[:300])
        audit("message.resolved", msg, f"Uncertain message resolved as {outcome}: {note}", actor=actor, contact=msg.contact)
    return OutboundMessage.objects.get(pk=msg.pk)
