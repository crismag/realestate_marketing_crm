"""Merge a duplicate contact into the one to keep (never automatic).

Everything that happened with the duplicate (inquiries, interactions, tasks, opportunities, messages, watches,
notifications) moves to the kept contact. The duplicate is archived with a pointer to the kept record, so old
links and the audit trail still work. Nothing is deleted.

Responsibility rule (ADR-001/002): merging cannot silently take a client away from someone. Both records must
already be held by the same person or the same pool, and neither may have a handover waiting. Otherwise the
person is told to hand one over first.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db.models import F

from crm.automation.models import Notification
from crm.comms.models import OutboundMessage
from crm.core import clock
from crm.core.db import require_version, write_transaction
from crm.core.errors import ConflictError, DomainError
from crm.core.services import audit
from crm.work.models import Assignment, Handover, Task

from .models import Contact, Inquiry, Interaction, Opportunity, Watch

LIFECYCLE_RANK = {"lead": 0, "prospect": 1, "client": 2}
FILLABLE = ("email", "phone", "source", "source_detail", "introducer", "referred_by", "preferred_channel",
            "next_contact_agreed_at")


@dataclass
class MergePlan:
    keep: Contact
    duplicate: Contact
    moves: dict[str, int]
    filled: list[str]
    blockers: list[str]


def plan_merge(keep: Contact, duplicate: Contact) -> MergePlan:
    blockers = []
    if keep.pk == duplicate.pk:
        blockers.append("Choose two different contacts.")
    if duplicate.merged_into_id or duplicate.archived_at:
        blockers.append(f"{duplicate.display_name} is already archived or merged.")
    if keep.archived_at:
        blockers.append(f"{keep.display_name} is archived. Keep an active record.")
    a_keep = Assignment.objects.select_related("user", "pool").filter(contact=keep).first()
    a_dup = Assignment.objects.select_related("user", "pool").filter(contact=duplicate).first()
    if a_keep and a_dup and (a_keep.kind, a_keep.user_id, a_keep.pool_id) != (a_dup.kind, a_dup.user_id, a_dup.pool_id):
        blockers.append(f"{keep.display_name} is held by {a_keep.describe()} and {duplicate.display_name} by "
                        f"{a_dup.describe()}. Hand one over so the same person or pool holds both, then merge.")
    if Handover.objects.filter(contact__in=[keep, duplicate], state="requested").exists():
        blockers.append("A handover is waiting on one of these contacts. Finish or cancel it first.")
    moves = {
        "inquiries": Inquiry.objects.filter(contact=duplicate).count(),
        "interactions": Interaction.objects.filter(contact=duplicate).count(),
        "tasks": Task.objects.filter(contact=duplicate).count(),
        "opportunities": Opportunity.objects.filter(contact=duplicate).count(),
        "customer messages": OutboundMessage.objects.filter(contact=duplicate).count(),
        "watchers": Watch.objects.filter(contact=duplicate).count(),
    }
    filled = [f for f in FILLABLE if not getattr(keep, f) and getattr(duplicate, f)]
    return MergePlan(keep, duplicate, moves, filled, blockers)


def can_merge(user, keep: Contact) -> bool:
    a = Assignment.objects.select_related("pool").filter(contact=keep).first()
    if a is None:
        return False
    if a.kind == "person":
        return a.user_id == user.pk
    return user in a.pool.accountable_users()


def merge_contacts(keep: Contact, duplicate: Contact, *, actor, keep_version: int, duplicate_version: int,
                   reason: str = "") -> Contact:
    require_version(keep_version)
    require_version(duplicate_version)

    def run():
        k = Contact.objects.get(pk=keep.pk)
        d = Contact.objects.get(pk=duplicate.pk)
        if k.version != keep_version or d.version != duplicate_version:
            raise ConflictError("One of the contacts changed since you opened this page. Review it again.",
                                code="stale_contact")
        plan = plan_merge(k, d)
        if plan.blockers:
            raise DomainError(plan.blockers[0], code="merge_blocked")
        if not can_merge(actor, k):
            raise DomainError("Only the person (or pool coordinator) responsible for these contacts can merge them.",
                              code="merge_not_allowed")
        now = clock.now()
        updates = {f: getattr(d, f) for f in plan.filled}
        notes = "\n\n".join(x for x in (k.notes, f"[Merged from {d.display_name}] {d.notes}" if d.notes else "") if x)
        interests = k.interests
        if d.interests and d.interests != k.interests:
            interests = "\n".join(x for x in (k.interests, d.interests) if x)
        lifecycle = max((k.lifecycle, d.lifecycle), key=lambda x: LIFECYCLE_RANK.get(x, 0))
        opt_out = k.email_opt_out or d.email_opt_out
        Inquiry.objects.filter(contact=d).update(contact=k)
        Interaction.objects.filter(contact=d).update(contact=k)
        Task.objects.filter(contact=d).update(contact=k)
        # Bump the version so a stage form opened on the duplicate cannot commit
        # against the moved deal, and so its audit cannot stay on the archived contact.
        Opportunity.objects.filter(contact=d).update(contact=k, version=F("version") + 1)
        OutboundMessage.objects.filter(contact=d).update(contact=k)
        Notification.objects.filter(contact=d).update(contact=k)
        existing_watchers = set(Watch.objects.filter(contact=k).values_list("user_id", flat=True))
        Watch.objects.filter(contact=d, user_id__in=existing_watchers).delete()
        Watch.objects.filter(contact=d).update(contact=k)
        Contact.objects.filter(pk=k.pk).update(
            **updates, notes=notes, interests=interests, lifecycle=lifecycle, email_opt_out=opt_out,
            email_opt_out_at=k.email_opt_out_at or d.email_opt_out_at, version=k.version + 1, updated_at=now)
        Contact.objects.filter(pk=d.pk).update(archived_at=now, merged_into=k, version=d.version + 1, updated_at=now)
        fresh = Contact.objects.get(pk=k.pk)
        if updates:
            # Keep the normalised lookup keys in step with the copied email/phone.
            fresh.save(update_fields=["email_normalized", "phone_normalized", "name_key"])
        moved = ", ".join(f"{n} {label}" for label, n in plan.moves.items() if n) or "no records"
        summary = f"Merged {d.display_name} (#{d.pk}) into this contact: moved {moved}"
        audit("contact.merged", fresh, summary + (f". Reason: {reason}" if reason else ""), actor=actor, contact=fresh,
              data={"duplicate_id": d.pk, "moves": plan.moves, "filled": plan.filled})
        audit("contact.merged_away", d, f"Merged into {fresh.display_name} (#{fresh.pk}) and archived", actor=actor,
              contact=d, data={"kept_id": fresh.pk})
        return fresh

    return write_transaction(run)
