"""Customer capture, search and relationship services (MOD-001, MOD-003)."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from django.db import IntegrityError
from django.db.models import F, Q, QuerySet

from crm.automation.queue import emit
from crm.core import clock
from crm.core.db import write_transaction
from crm.core.errors import ConflictError, DomainError
from crm.core.services import audit
from crm.work.models import Assignment, AssignmentEvent, Pool

from .models import Contact, Inquiry, Interaction, Opportunity, Source, Watch, name_key, normalize_email, normalize_phone

CONTACT_EDITABLE_FIELDS = (
    "display_name", "email", "phone", "source", "source_detail", "introducer", "interests", "notes",
    "preferred_channel", "next_contact_agreed_at",
)
HUMAN_RESPONSE_KINDS = ("outbound_attempt", "conversation", "meeting_tour")


def _email_variants(email: str) -> set[str]:
    """The address itself plus its form without a "+tag" (jane+web@x.com -> jane@x.com)."""
    value = normalize_email(email)
    if "@" not in value:
        return {value} if value else set()
    local, _, domain = value.partition("@")
    return {value, f"{local.split('+', 1)[0]}@{domain}"}


def duplicate_candidates(*, email: str = "", phone: str = "", name: str = "", exclude_id: int | None = None) -> QuerySet:
    """Possible duplicates. Never merges automatically.

    Matches (implementation default, C-R6): normalised email, including the address without a "+tag";
    the last 10 phone digits; and the name compared ignoring case, accents, punctuation and word order
    ("Smith, John" = "john smith"). A name match only counts for names of two or more words, so a single
    first name does not flag everyone who shares it.
    """
    query = Q()
    emails = _email_variants(email)
    for variant in emails:
        query |= Q(email_normalized=variant) | Q(email_normalized__startswith=variant.split("@")[0] + "+",
                                                 email_normalized__endswith="@" + variant.split("@")[-1])
    if normalize_phone(phone) and len(normalize_phone(phone)) >= 7:
        query |= Q(phone_normalized=normalize_phone(phone))
    if name.strip():
        query |= Q(display_name__iexact=name.strip())
        key = name_key(name)
        if len(key.split()) >= 2:
            query |= Q(name_key=key)
    if not query:
        return Contact.objects.none()
    qs = Contact.objects.filter(query).select_related("assignment__user", "assignment__pool")
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs[:10]


def match_reasons(candidate: Contact, *, email: str = "", phone: str = "", name: str = "") -> list[str]:
    """Why a candidate was suggested, so the person can judge it (shown next to each candidate)."""
    reasons = []
    mine = {e.split("@")[0].split("+")[0] + "@" + e.split("@")[-1] for e in _email_variants(email) if "@" in e}
    theirs = {e.split("@")[0].split("+")[0] + "@" + e.split("@")[-1] for e in _email_variants(candidate.email) if "@" in e}
    if mine & theirs:
        reasons.append("same email" if normalize_email(email) == candidate.email_normalized else "same email apart from a +tag")
    if normalize_phone(phone) and len(normalize_phone(phone)) >= 7 and normalize_phone(phone) == candidate.phone_normalized:
        reasons.append("same phone")
    if name.strip() and (candidate.display_name.lower() == name.strip().lower()
                         or (len(name_key(name).split()) >= 2 and candidate.name_key == name_key(name))):
        reasons.append("same name" if candidate.display_name.lower() == name.strip().lower() else "same name, different order or spelling marks")
    return reasons


@dataclass
class CaptureResult:
    contact: Contact
    inquiry: Inquiry | None


def capture_contact(*, actor, data: dict, destination: str, pool: Pool | None = None,
                    inquiry_message: str = "", inquiry_channel: str = "other") -> CaptureResult:
    """Create a contact with initial responsibility (the capturing user or a pool) and optional inquiry."""
    if destination not in ("me", "pool"):
        raise DomainError("Choose who is responsible: yourself or a shared pool.", code="invalid_destination")
    if destination == "pool" and (pool is None or not pool.active):
        raise DomainError("Choose an active pool.", code="invalid_destination")

    def run():
        now = clock.now()
        fields = {k: v for k, v in data.items() if k in CONTACT_EDITABLE_FIELDS}
        contact = Contact(created_by=actor, created_at=now, updated_at=now, **fields)
        contact.save()
        assignment = Assignment.objects.create(
            contact=contact,
            kind="person" if destination == "me" else "pool",
            user=actor if destination == "me" else None,
            pool=pool if destination == "pool" else None,
            since=now,
        )
        AssignmentEvent.objects.create(
            contact=contact, event_type="created", to_user=assignment.user, to_pool=assignment.pool, actor=actor,
            reason="Initial responsibility at capture", operation_key=f"create:{contact.pk}", version_after=1, occurred_at=now,
        )
        inquiry = None
        if inquiry_message.strip():
            inquiry = Inquiry.objects.create(
                contact=contact, source=contact.source, channel=inquiry_channel, message=inquiry_message.strip(),
                received_at=now, recorded_at=now, recorded_by=actor,
            )
            emit("inquiry_received", inquiry_id=inquiry.pk, event_key=f"inquiry:{inquiry.pk}")
        audit("contact.created", contact, f"Captured {contact.display_name} ({assignment.describe()})", actor=actor, contact=contact)
        return CaptureResult(contact, inquiry)

    return write_transaction(run)


def update_contact(contact: Contact, *, actor, data: dict, expected_version: int) -> Contact:
    def run():
        fields = {k: v for k, v in data.items() if k in CONTACT_EDITABLE_FIELDS}
        current = Contact.objects.get(pk=contact.pk)
        changes = {k: [str(getattr(current, k)), str(v)] for k, v in fields.items() if getattr(current, k) != v}
        if not changes:
            return current
        fields["email_normalized"] = normalize_email(fields.get("email", current.email))
        fields["phone_normalized"] = normalize_phone(fields.get("phone", current.phone))
        fields["name_key"] = name_key(fields.get("display_name", current.display_name))
        updated = Contact.objects.filter(pk=contact.pk, version=expected_version).update(
            version=expected_version + 1, updated_at=clock.now(), **fields
        )
        if updated != 1:
            raise ConflictError("This contact was changed by someone else. Your edits were not saved; review the latest version.")
        fresh = Contact.objects.get(pk=contact.pk)
        audit("contact.updated", fresh, f"Updated {', '.join(sorted(changes))}", actor=actor, contact=fresh,
              data={"fields": sorted(changes)})
        emit("contact_updated", contact_id=fresh.pk, actor_id=actor.pk, fields=sorted(changes))
        return fresh

    return write_transaction(run)


def set_lifecycle(contact: Contact, *, actor, lifecycle: str, disposition: str, reason: str, expected_version: int) -> Contact:
    if lifecycle not in dict(Contact._meta.get_field("lifecycle").choices):
        raise DomainError("Unknown lifecycle.", code="invalid_lifecycle")
    if disposition not in dict(Contact._meta.get_field("disposition").choices):
        raise DomainError("Unknown disposition.", code="invalid_disposition")
    if disposition in ("inactive", "disqualified") and not reason.strip():
        raise DomainError("Give a reason when marking a relationship inactive or disqualified.", code="reason_required")

    def run():
        current = Contact.objects.get(pk=contact.pk)
        updated = Contact.objects.filter(pk=contact.pk, version=expected_version).update(
            lifecycle=lifecycle, disposition=disposition, disposition_reason=reason.strip()[:200],
            version=expected_version + 1, updated_at=clock.now(),
        )
        if updated != 1:
            raise ConflictError("This contact was changed by someone else. Reload and try again.")
        fresh = Contact.objects.get(pk=contact.pk)
        audit("contact.lifecycle", fresh,
              f"Lifecycle {current.lifecycle}->{lifecycle}, disposition {current.disposition}->{disposition}",
              actor=actor, contact=fresh, data={"reason": reason})
        if current.lifecycle != "client" and lifecycle == "client":
            emit("became_client", contact_id=fresh.pk, event_key=f"client:{fresh.pk}")
        emit("contact_updated", contact_id=fresh.pk, actor_id=actor.pk, fields=["lifecycle"])
        return fresh

    return write_transaction(run)


def set_email_opt_out(contact: Contact, *, actor, opted_out: bool) -> Contact:
    def run():
        Contact.objects.filter(pk=contact.pk).update(
            email_opt_out=opted_out, email_opt_out_at=clock.now() if opted_out else None, updated_at=clock.now()
        )
        fresh = Contact.objects.get(pk=contact.pk)
        audit("contact.opt_out" if opted_out else "contact.opt_in", fresh,
              "Customer opted out of email" if opted_out else "Email opt-out removed", actor=actor, contact=fresh)
        return fresh

    return write_transaction(run)


def archive_contact(contact: Contact, *, actor, reason: str) -> Contact:
    if not reason.strip():
        raise DomainError("Give a reason for archiving.", code="reason_required")

    def run():
        Contact.objects.filter(pk=contact.pk).update(archived_at=clock.now(), updated_at=clock.now())
        fresh = Contact.objects.get(pk=contact.pk)
        audit("contact.archived", fresh, f"Archived: {reason}", actor=actor, contact=fresh)
        return fresh

    return write_transaction(run)


def record_inquiry(contact: Contact, *, actor, message: str, channel: str, source: Source | None,
                   received_at=None, external_key: str | None = None) -> Inquiry:
    """Record a (repeat) inquiry on an existing identity. ``external_key`` makes intake replays idempotent."""
    if not message.strip():
        raise DomainError("Describe the inquiry.", code="message_required")

    def run():
        if external_key:
            existing = Inquiry.objects.filter(external_key=external_key).first()
            if existing:
                return existing
        now = clock.now()
        inquiry = Inquiry.objects.create(
            contact=contact, source=source or contact.source, channel=channel, message=message.strip(),
            received_at=received_at or now, recorded_at=now, recorded_by=actor, external_key=external_key,
        )
        audit("inquiry.recorded", inquiry, f"Inquiry recorded via {channel}", actor=actor, contact=contact)
        emit("inquiry_received", inquiry_id=inquiry.pk, event_key=f"inquiry:{inquiry.pk}")
        return inquiry

    try:
        return write_transaction(run)
    except IntegrityError:
        if external_key:
            return Inquiry.objects.get(external_key=external_key)
        raise


def close_inquiry(inquiry: Inquiry, *, actor, reason: str) -> Inquiry:
    if not reason.strip():
        raise DomainError("Give a reason for closing without a response.", code="reason_required")

    def run():
        updated = Inquiry.objects.filter(pk=inquiry.pk, status="awaiting").update(status="closed")
        if updated != 1:
            raise ConflictError("This inquiry is no longer awaiting a response.")
        audit("inquiry.closed", inquiry, f"Inquiry closed without response: {reason}", actor=actor, contact=inquiry.contact)
        return Inquiry.objects.get(pk=inquiry.pk)

    return write_transaction(run)


def record_interaction(contact: Contact, *, actor, kind: str, channel: str, summary: str, occurred_at,
                       inquiry: Inquiry | None = None) -> Interaction:
    """Log human interaction evidence. Future-dated interactions are rejected."""
    from crm.core.policy import INTERACTION_TYPES

    if kind not in dict(INTERACTION_TYPES):
        raise DomainError("Unknown interaction type.", code="invalid_kind")
    if not summary.strip():
        raise DomainError("Summarise what happened.", code="summary_required")
    now = clock.now()
    if occurred_at > now:
        raise DomainError("An interaction cannot be in the future. Create a task for planned work.", code="future_interaction")
    if inquiry is not None and inquiry.contact_id != contact.pk:
        raise DomainError("That inquiry belongs to another contact.", code="inquiry_mismatch")

    def run():
        interaction = Interaction.objects.create(
            contact=contact, kind=kind, channel=channel, summary=summary.strip(), occurred_at=occurred_at,
            recorded_at=now, actor=actor, inquiry=inquiry,
        )
        if inquiry is not None and kind in HUMAN_RESPONSE_KINDS:
            Inquiry.objects.filter(pk=inquiry.pk, status="awaiting").update(
                status="responded", responded_at=occurred_at, response_interaction=interaction
            )
        if kind == "inbound_reply":
            emit("customer_replied", contact_id=contact.pk, interaction_id=interaction.pk)
        audit("interaction.recorded", interaction, f"{interaction.get_kind_display()} via {channel}", actor=actor, contact=contact)
        emit("contact_activity", contact_id=contact.pk, actor_id=actor.pk, interaction_id=interaction.pk)
        return interaction

    return write_transaction(run)


def save_opportunity(contact: Contact, *, actor, opportunity: Opportunity | None, data: dict, expected_version: int | None):
    allowed = ("title", "stage", "amount_minor", "currency", "expected_close")

    def run():
        fields = {k: v for k, v in data.items() if k in allowed}
        if opportunity is None:
            now = clock.now()
            opp = Opportunity.objects.create(contact=contact, created_by=actor, created_at=now, stage_changed_at=now, **fields)
            audit("opportunity.created", opp, f"Opportunity '{opp.title}' created", actor=actor, contact=contact)
            return opp
        if opportunity.outcome != "open":
            raise DomainError("Closed opportunities cannot be edited. Reopen it first.", code="closed")
        stage_changed = "stage" in fields and fields["stage"] != opportunity.stage
        if stage_changed:
            # Only a real stage change moves the clock used by the stalled-opportunity reason (C-R2).
            fields["stage_changed_at"] = clock.now()
        updated = Opportunity.objects.filter(pk=opportunity.pk, version=expected_version).update(
            version=expected_version + 1, **fields
        )
        if updated != 1:
            raise ConflictError("This opportunity was changed by someone else. Reload and try again.")
        opp = Opportunity.objects.get(pk=opportunity.pk)
        audit("opportunity.updated", opp, f"Opportunity '{opp.title}' updated (stage {opp.stage})", actor=actor, contact=contact)
        if stage_changed:
            audit("opportunity.stage_changed", opp, f"Opportunity '{opp.title}' stage {opportunity.stage} -> {opp.stage}",
                  actor=actor, contact=contact, data={"from": opportunity.stage, "to": opp.stage})
        return opp

    return write_transaction(run)


def close_opportunity(opportunity: Opportunity, *, actor, outcome: str, reason: str, expected_version: int, policy: dict):
    if outcome not in ("won", "lost", "open"):
        raise DomainError("Unknown outcome.", code="invalid_outcome")

    def run():
        now = clock.now()
        updated = Opportunity.objects.filter(pk=opportunity.pk, version=expected_version).update(
            outcome=outcome, closed_at=None if outcome == "open" else now, outcome_reason=reason.strip()[:200],
            version=expected_version + 1,
        )
        if updated != 1:
            raise ConflictError("This opportunity was changed by someone else. Reload and try again.")
        opp = Opportunity.objects.get(pk=opportunity.pk)
        label = "reopened" if outcome == "open" else f"marked {outcome}"
        audit("opportunity.outcome", opp, f"Opportunity '{opp.title}' {label}", actor=actor, contact=opp.contact, data={"reason": reason})
        contact = opp.contact
        if outcome == "won" and policy.get("client_milestone") == "opportunity_won" and contact.lifecycle != "client":
            Contact.objects.filter(pk=contact.pk).update(lifecycle="client", version=F("version") + 1, updated_at=now)
            audit("contact.lifecycle", contact, "Lifecycle -> client (opportunity won; implementation-default milestone)",
                  actor=actor, contact=contact)
            emit("became_client", contact_id=contact.pk, event_key=f"client:{contact.pk}")
        return opp

    return write_transaction(run)


def watch(contact: Contact, *, actor, reason: str = "") -> Watch:
    def run():
        obj, created = Watch.objects.get_or_create(user=actor, contact=contact, defaults={"reason": reason[:200]})
        if created:
            audit("watch.added", obj, "Started watching", actor=actor, contact=contact)
        return obj

    return write_transaction(run)


def unwatch(contact: Contact, *, actor) -> None:
    def run():
        deleted, _ = Watch.objects.filter(user=actor, contact=contact).delete()
        if deleted:
            audit("watch.removed", contact, "Stopped watching", actor=actor, contact=contact)

    write_transaction(run)


def search_contacts(*, q: str = "", lifecycle: str = "", responsibility: str = "", user=None, pool_id: str = "",
                    source_id: str = "", include_archived: bool = False, sort: str = "name") -> QuerySet:
    qs = Contact.objects.select_related("assignment__user", "assignment__pool", "source")
    if not include_archived:
        qs = qs.filter(archived_at__isnull=True)
    q = q.strip()
    if q:
        digits = normalize_phone(q)
        cond = Q(display_name__icontains=q) | Q(email_normalized__icontains=q.lower()) | Q(interests__icontains=q)
        if len(digits) >= 4:
            cond |= Q(phone_normalized__contains=digits)
        qs = qs.filter(cond)
    if lifecycle:
        qs = qs.filter(lifecycle=lifecycle)
    if responsibility == "mine" and user is not None:
        qs = qs.filter(assignment__kind="person", assignment__user=user)
    elif responsibility == "pool":
        qs = qs.filter(assignment__kind="pool")
    if pool_id.isdigit():
        qs = qs.filter(assignment__pool_id=int(pool_id))
    if source_id.isdigit():
        qs = qs.filter(source_id=int(source_id))
    order = {
        "name": ["display_name", "id"],
        "-created": ["-created_at", "-id"],
        "created": ["created_at", "id"],
        "-updated": ["-updated_at", "-id"],
    }.get(sort, ["display_name", "id"])
    return qs.order_by(*order)


MAX_ID = 2**63 - 1


def followup_suggestion(contact: Contact, *, user, interaction_ref: str, policy: dict) -> dict | None:
    """C-R3: a pre-filled follow-up task after `user` logs an interaction. Nothing is created here.

    Offered only for the interaction this user just logged (by id, within an hour), for interaction types
    configured in policy, and when the contact has no open task due in the future.
    """
    config = policy.get("followup_suggestions") or {}
    if not config.get("enabled") or not interaction_ref.isdigit() or len(interaction_ref) > 19:
        return None
    interaction_id = int(interaction_ref)
    if interaction_id > MAX_ID:
        return None
    now = clock.now()
    interaction = Interaction.objects.filter(pk=interaction_id, contact=contact, actor=user,
                                             recorded_at__gte=now - dt.timedelta(hours=1)).first()
    rule = (config.get("by_kind") or {}).get(interaction.kind) if interaction else None
    if not rule:
        return None
    if contact.tasks.filter(status="open", due_at__gte=now).exists():
        return None
    return {"interaction": interaction, "title": str(rule["title"])[:200],
            "due_at": now + dt.timedelta(hours=int(rule.get("hours", 24)))}
