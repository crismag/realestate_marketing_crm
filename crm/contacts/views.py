from __future__ import annotations

import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from crm.attention import services as attention
from crm.comms.models import OutboundMessage
from crm.core import clock
from crm.core.errors import DomainError
from crm.core.models import AuditEvent
from crm.core.services import audit, get_policy
from crm.core.web import new_operation_id, paginate, run_action
from crm.work.forms import TaskForm
from crm.work.models import Assignment, AssignmentEvent, Handover, Pool
from crm.work.services import can_decide, can_initiate_handover

from . import importing, merging, services
from .forms import (
    CaptureForm,
    ContactFieldsForm,
    ImportUploadForm,
    InquiryForm,
    InteractionForm,
    LifecycleForm,
    OpportunityForm,
    OpportunityOutcomeForm,
)
from .models import LIFECYCLES, Contact, ContactImport, Inquiry, Opportunity, Source, Watch

User = get_user_model()
TIMELINE_AUDIT_ACTIONS = {
    "contact.created", "contact.updated", "contact.lifecycle", "contact.opt_out", "contact.opt_in", "contact.archived",
    "task.created", "task.completed", "task.cancelled", "task.replanned", "task.reassigned", "handover.requested",
    "handover.accepted", "handover.declined", "handover.cancelled", "handover.stale", "opportunity.created",
    "opportunity.outcome", "opportunity.stage_changed", "attention.snoozed", "attention.unsnoozed", "inquiry.closed", "watch.added", "watch.removed",
}


def contact_list(request):
    params = {k: request.GET.get(k, "") for k in ("q", "lifecycle", "responsibility", "pool", "source", "sort")}
    qs = services.search_contacts(q=params["q"], lifecycle=params["lifecycle"], responsibility=params["responsibility"],
                                  user=request.user, pool_id=params["pool"], source_id=params["source"],
                                  include_archived=request.GET.get("archived") == "1", sort=params["sort"] or "name")
    if request.GET.get("format") == "csv":
        return export_csv(request, qs)
    page, querystring = paginate(request, qs)
    return render(request, "contacts/list.html", {
        "page": page, "querystring": querystring, "params": params, "lifecycles": LIFECYCLES,
        "pools": Pool.objects.filter(active=True), "sources": Source.objects.all(),
        "filtered": any(params[k] for k in ("q", "lifecycle", "responsibility", "pool", "source")),
    })


def _csv_safe(value) -> str:
    """Neutralise spreadsheet formula injection (=, +, -, @, tab, CR at the start of a cell)."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def export_csv(request, qs):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="contacts.csv"'
    writer = csv.writer(response)
    writer.writerow(["id", "name", "email", "phone", "lifecycle", "disposition", "responsible", "source", "created_at_utc"])
    count = 0
    for c in qs[:5000]:
        a = getattr(c, "assignment", None)
        writer.writerow([_csv_safe(v) for v in (c.pk, c.display_name, c.email, c.phone, c.lifecycle, c.disposition,
                                                a.describe() if a else "", c.source.label if c.source else "",
                                                c.created_at.isoformat())])
        count += 1
    audit("contacts.exported", None, f"Exported {count} contacts to CSV", actor=request.user, data={"rows": count})
    return response


def contact_new(request):
    form = CaptureForm(request.POST or None, initial={"destination": "me"})
    duplicates = []
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        duplicates = list(services.duplicate_candidates(email=d["email"], phone=d["phone"], name=d["display_name"]))
        for dup in duplicates:
            dup.match_reasons = services.match_reasons(dup, email=d["email"], phone=d["phone"], name=d["display_name"])
        if duplicates and not d["confirm_new"]:
            messages.warning(request, "Possible existing contacts found. Open one to add a repeat inquiry, or confirm this is a different person.")
        else:
            data = {k: d.get(k) for k in services.CONTACT_EDITABLE_FIELDS}
            data = {k: (v if v is not None else "") if k not in ("source", "introducer", "next_contact_agreed_at") else v
                    for k, v in data.items()}
            try:
                result = services.capture_contact(actor=request.user, data=data, destination=d["destination"],
                                                  pool=d.get("pool"), inquiry_message=d.get("inquiry_message") or "",
                                                  inquiry_channel=d.get("inquiry_channel") or "other")
            except DomainError as exc:
                form.add_error(None, exc.message)
            else:
                messages.success(request, f"{result.contact.display_name} captured.")
                return redirect("contacts:detail", pk=result.contact.pk)
    return render(request, "contacts/new.html", {"form": form, "duplicates": duplicates})


def _timeline(contact):
    entries = []
    for i in contact.interactions.select_related("actor"):
        entries.append({"at": i.occurred_at, "kind": "interaction", "title": i.get_kind_display(),
                        "meta": f"{i.get_channel_display()} · {i.actor or 'system'} · recorded {i.recorded_at:%Y-%m-%d %H:%M} UTC",
                        "body": i.summary})
    for q in contact.inquiries.all():
        entries.append({"at": q.received_at, "kind": "inquiry", "title": f"Inquiry ({q.get_status_display().lower()})",
                        "meta": q.get_channel_display(), "body": q.message})
    for e in AssignmentEvent.objects.filter(contact=contact).select_related("from_user", "from_pool", "to_user", "to_pool", "actor"):
        frm = e.from_user or (f"pool {e.from_pool}" if e.from_pool else "—")
        to = e.to_user or (f"pool {e.to_pool}" if e.to_pool else "—")
        entries.append({"at": e.occurred_at, "kind": "assignment", "title": e.get_event_type_display(),
                        "meta": f"{frm} → {to} · by {e.actor}", "body": e.reason})
    for m in contact.outbound_messages.all():
        entries.append({"at": m.attempted_at or m.created_at, "kind": "message", "title": f"Automated email: {m.get_status_display()}",
                        "meta": m.subject or (m.template.name if m.template else ""), "body": m.status_reason})
    for a in AuditEvent.objects.filter(contact=contact, action__in=TIMELINE_AUDIT_ACTIONS).select_related("actor")[:200]:
        entries.append({"at": a.occurred_at, "kind": "audit", "title": a.summary, "meta": f"{a.actor or a.actor_kind}", "body": ""})
    entries.sort(key=lambda e: e["at"], reverse=True)
    return entries[:150]


def render_detail(request, contact, *, status=200, **forms):
    policy = get_policy()
    suggestion = None if forms.get("task_form") else services.followup_suggestion(
        contact, user=request.user, interaction_ref=request.GET.get("suggest", ""), policy=policy)
    task_initial = {"assignee": request.user}
    if suggestion:
        task_initial.update({"title": suggestion["title"], "kind": "follow_up", "due_at": suggestion["due_at"]})
    assignment = Assignment.objects.select_related("user", "pool__coordinator", "pool__backup_coordinator").filter(contact=contact).first()
    items = attention.evaluate(policy=policy, contact_ids=[contact.pk])
    open_handover = Handover.objects.filter(contact=contact, state="requested").select_related("sender", "recipient", "pool").first()
    stages = policy["opportunity_stages"]
    ctx = {
        "contact": contact,
        "assignment": assignment,
        "attention": items[0] if items else None,
        "tasks": contact.tasks.select_related("assignee").order_by("status", "due_at"),
        "open_tasks": contact.tasks.filter(status="open").select_related("assignee").order_by("due_at"),
        "inquiries": contact.inquiries.all()[:20],
        "opportunities": contact.opportunities.all(),
        "stage_labels": {s["code"]: s["label"] for s in stages},
        "handovers": contact.handovers.select_related("sender", "recipient", "pool", "decided_by")[:10],
        "open_handover": open_handover,
        "can_handover": assignment is not None and can_initiate_handover(assignment, request.user) and open_handover is None,
        "can_decide": open_handover is not None and can_decide(open_handover, request.user),
        "is_sender": open_handover is not None and open_handover.sender_id == request.user.pk,
        "watching": Watch.objects.filter(user=request.user, contact=contact).exists(),
        "watchers": Watch.objects.filter(contact=contact).select_related("user"),
        "timeline": _timeline(contact),
        "messages_out": OutboundMessage.objects.filter(contact=contact)[:10],
        "interaction_form": forms.get("interaction_form") or InteractionForm(contact=contact, prefix="ix"),
        "task_form": forms.get("task_form") or TaskForm(prefix="task", initial=task_initial),
        "followup_suggestion": suggestion,
        "inquiry_form": forms.get("inquiry_form") or InquiryForm(prefix="inq"),
        "lifecycle_form": forms.get("lifecycle_form") or LifecycleForm(prefix="lc", initial={
            "lifecycle": contact.lifecycle, "disposition": contact.disposition, "reason": contact.disposition_reason,
            "version": contact.version}),
        "opportunity_form": forms.get("opportunity_form") or OpportunityForm(prefix="opp", stages=stages),
        "operation_id": new_operation_id(),
        "lifecycle_labels": policy["lifecycle_labels"],
        "now": clock.now(),
        "snoozable": attention.SNOOZABLE,
        "possible_duplicates": [] if contact.archived_at else [
            d for d in services.duplicate_candidates(email=contact.email, phone=contact.phone, name=contact.display_name,
                                                     exclude_id=contact.pk) if d.archived_at is None][:5],
        "can_merge": merging.can_merge(request.user, contact),
    }
    return render(request, "contacts/detail.html", ctx, status=status)


def contact_detail(request, pk):
    contact = get_object_or_404(Contact.objects.select_related("source", "introducer", "referred_by", "created_by"), pk=pk)
    return render_detail(request, contact)


def contact_edit(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    initial = {f: getattr(contact, f) for f in services.CONTACT_EDITABLE_FIELDS}
    form = ContactFieldsForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            expected = int(request.POST.get("version", "0"))
        except ValueError:
            expected = 0
        data = {k: v if v is not None or k in ("source", "introducer", "next_contact_agreed_at") else ""
                for k, v in form.cleaned_data.items()}
        try:
            services.update_contact(contact, actor=request.user, data=data, expected_version=expected)
        except DomainError as exc:
            form.add_error(None, exc.message)
            contact.refresh_from_db()
        else:
            messages.success(request, "Contact saved.")
            return redirect("contacts:detail", pk=pk)
    duplicates = services.duplicate_candidates(email=contact.email, phone=contact.phone, name="", exclude_id=contact.pk)
    return render(request, "contacts/edit.html", {"form": form, "contact": contact, "duplicates": duplicates,
                                                  "version": request.POST.get("version", contact.version)})


@require_POST
def contact_lifecycle(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    form = LifecycleForm(request.POST, prefix="lc")
    if not form.is_valid():
        return render_detail(request, contact, lifecycle_form=form, status=400)
    d = form.cleaned_data
    response, _ = run_action(request, lambda: services.set_lifecycle(
        contact, actor=request.user, lifecycle=d["lifecycle"], disposition=d["disposition"], reason=d["reason"],
        expected_version=d["version"]), success="Lifecycle updated.", redirect_to=f"/contacts/{pk}/")
    return response


@require_POST
def contact_opt_out(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    opted = request.POST.get("opt_out") == "1"
    response, _ = run_action(request, lambda: services.set_email_opt_out(contact, actor=request.user, opted_out=opted),
                             success="Email preference saved.", redirect_to=f"/contacts/{pk}/")
    return response


@require_POST
def contact_archive(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    response, _ = run_action(request, lambda: services.archive_contact(contact, actor=request.user,
                                                                       reason=request.POST.get("reason", "")),
                             success="Contact archived. History is kept.", redirect_to=f"/contacts/{pk}/")
    return response


@require_POST
def add_inquiry(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    form = InquiryForm(request.POST, prefix="inq")
    if not form.is_valid():
        return render_detail(request, contact, inquiry_form=form, status=400)
    d = form.cleaned_data
    try:
        services.record_inquiry(contact, actor=request.user, message=d["message"], channel=d["channel"], source=d["source"],
                                received_at=d["received_at"])
    except DomainError as exc:
        form.add_error(None, exc.message)
        return render_detail(request, contact, inquiry_form=form, status=400)
    messages.success(request, "Inquiry recorded; it awaits a response.")
    return redirect("contacts:detail", pk=pk)


@require_POST
def close_inquiry(request, pk, inquiry_id):
    inquiry = get_object_or_404(Inquiry, pk=inquiry_id, contact_id=pk)
    response, _ = run_action(request, lambda: services.close_inquiry(inquiry, actor=request.user,
                                                                     reason=request.POST.get("reason", "")),
                             success="Inquiry closed.", redirect_to=f"/contacts/{pk}/")
    return response


@require_POST
def add_interaction(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    form = InteractionForm(request.POST, contact=contact, prefix="ix")
    if not form.is_valid():
        return render_detail(request, contact, interaction_form=form, status=400)
    d = form.cleaned_data
    try:
        interaction = services.record_interaction(contact, actor=request.user, kind=d["kind"], channel=d["channel"],
                                                  summary=d["summary"], occurred_at=d["occurred_at"] or clock.now(),
                                                  inquiry=d["inquiry"])
    except DomainError as exc:
        form.add_error(None, exc.message)
        return render_detail(request, contact, interaction_form=form, status=400)
    messages.success(request, "Interaction logged.")
    return redirect(f"{reverse('contacts:detail', args=[pk])}?suggest={interaction.pk}#next")


@require_POST
def toggle_watch(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    if request.POST.get("watch") == "1":
        services.watch(contact, actor=request.user, reason=request.POST.get("reason", ""))
        messages.success(request, "You are watching this client. You will be notified of activity; responsibility is unchanged.")
    else:
        services.unwatch(contact, actor=request.user)
        messages.success(request, "You stopped watching this client.")
    return redirect("contacts:detail", pk=pk)


def _amount_minor(amount: Decimal | None):
    return None if amount is None else int((amount * 100).quantize(Decimal("1")))


@require_POST
def add_opportunity(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    policy = get_policy()
    form = OpportunityForm(request.POST, prefix="opp", stages=policy["opportunity_stages"])
    if not form.is_valid():
        return render_detail(request, contact, opportunity_form=form, status=400)
    d = form.cleaned_data
    services.save_opportunity(contact, actor=request.user, opportunity=None, expected_version=None, data={
        "title": d["title"], "stage": d["stage"], "amount_minor": _amount_minor(d["amount"]),
        "currency": policy["currency"] if d["amount"] is not None else "", "expected_close": d["expected_close"]})
    messages.success(request, "Opportunity added.")
    return redirect("contacts:detail", pk=pk)


def opportunity_edit(request, pk, opp_id):
    opp = get_object_or_404(Opportunity.objects.select_related("contact"), pk=opp_id, contact_id=pk)
    policy = get_policy()
    initial = {"title": opp.title, "stage": opp.stage, "expected_close": opp.expected_close, "version": opp.version,
               "amount": (Decimal(opp.amount_minor) / 100) if opp.amount_minor is not None else None}
    form = OpportunityForm(request.POST or None, initial=initial, stages=policy["opportunity_stages"])
    outcome_form = OpportunityOutcomeForm(initial={"version": opp.version, "outcome": "won"})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            services.save_opportunity(opp.contact, actor=request.user, opportunity=opp, expected_version=d["version"] or 0, data={
                "title": d["title"], "stage": d["stage"], "amount_minor": _amount_minor(d["amount"]),
                "currency": policy["currency"] if d["amount"] is not None else "", "expected_close": d["expected_close"]})
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            messages.success(request, "Opportunity saved.")
            return redirect("contacts:detail", pk=pk)
    return render(request, "contacts/opportunity.html", {"form": form, "outcome_form": outcome_form, "opp": opp,
                                                         "contact": opp.contact})


@require_POST
def opportunity_outcome(request, pk, opp_id):
    opp = get_object_or_404(Opportunity, pk=opp_id, contact_id=pk)
    form = OpportunityOutcomeForm(request.POST)
    if not form.is_valid():
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
        return redirect("contacts:opportunity", pk=pk, opp_id=opp_id)
    d = form.cleaned_data
    response, _ = run_action(request, lambda: services.close_opportunity(
        opp, actor=request.user, outcome=d["outcome"], reason=d["reason"], expected_version=d["version"], policy=get_policy()),
        success="Opportunity outcome recorded.", redirect_to=f"/contacts/{pk}/")
    return response


def opportunities(request):
    policy = get_policy()
    outcome = request.GET.get("outcome", "open")
    qs = Opportunity.objects.select_related("contact__assignment__user", "contact__assignment__pool").order_by("-created_at")
    if outcome in ("open", "won", "lost"):
        qs = qs.filter(outcome=outcome)
    stage = request.GET.get("stage", "")
    if stage:
        qs = qs.filter(stage=stage)
    page, querystring = paginate(request, qs)
    return render(request, "contacts/opportunities.html", {
        "page": page, "querystring": querystring, "outcome": outcome, "stage": stage, "stages": policy["opportunity_stages"],
        "stage_labels": {s["code"]: s["label"] for s in policy["opportunity_stages"]}, "currency": policy["currency"],
    })



def import_start(request):
    form = ImportUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            imp = importing.parse_upload(actor=request.user, upload=d["file"], destination=d["destination"], pool=d.get("pool"),
                                         default_source=d.get("default_source"), policy=get_policy())
        except DomainError as exc:
            form.add_error("file", exc.message)
        else:
            return redirect("contacts:import_detail", pk=imp.pk)
    recent = ContactImport.objects.filter(created_by=request.user).only(
        "id", "filename", "status", "created_at", "summary")[:10]
    return render(request, "contacts/import.html", {"form": form, "recent": recent})


def import_detail(request, pk):
    imp = get_object_or_404(ContactImport.objects.select_related("pool", "default_source", "created_by"), pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "cancel":
                importing.cancel_import(imp, actor=request.user)
                messages.info(request, "Import cancelled. Nothing was added.")
                return redirect("contacts:import")
            imp = importing.run_import(imp, actor=request.user, include_duplicates=request.POST.get("include_duplicates") == "1")
        except DomainError as exc:
            messages.error(request, exc.message)
        else:
            messages.success(request, f"Imported {imp.summary['created']} contact(s).")
        return redirect("contacts:import_detail", pk=imp.pk)
    headers = list(imp.columns)
    return render(request, "contacts/import_detail.html", {
        "imp": imp, "counts": importing.counts(imp), "rows": imp.rows[:300], "more": max(0, len(imp.rows) - 300),
        "recognised": headers, "field_labels": FIELD_LABELS,
        "is_owner": imp.created_by_id == request.user.pk,
    })


FIELD_LABELS = {"display_name": "Name", "first_name": "First name", "last_name": "Last name", "email": "Email", "phone": "Phone",
                "source": "Source", "source_detail": "Source detail", "interests": "Interests", "notes": "Notes",
                "lifecycle": "Lifecycle"}


def import_template(request):
    response = HttpResponse(importing.template_csv(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="contacts-import-template.csv"'
    return response


def contact_merge(request, pk, duplicate_pk):
    keep = get_object_or_404(Contact, pk=pk)
    duplicate = get_object_or_404(Contact, pk=duplicate_pk)
    plan = merging.plan_merge(keep, duplicate)
    if not merging.can_merge(request.user, keep):
        plan.blockers.append("Only the person (or pool coordinator) responsible for these contacts can merge them.")
    if request.method == "POST":
        try:
            merging.merge_contacts(keep, duplicate, actor=request.user,
                                   keep_version=int(request.POST.get("keep_version", 0)),
                                   duplicate_version=int(request.POST.get("duplicate_version", 0)),
                                   reason=request.POST.get("reason", "")[:200])
        except (DomainError, ValueError) as exc:
            messages.error(request, getattr(exc, "message", "Could not merge."))
            return redirect("contacts:merge", pk=keep.pk, duplicate_pk=duplicate.pk)
        messages.success(request, f"Merged {duplicate.display_name} into {keep.display_name}. The duplicate is archived.")
        return redirect("contacts:detail", pk=keep.pk)
    return render(request, "contacts/merge.html", {"plan": plan, "keep": keep, "duplicate": duplicate,
                                                   "field_labels": {f: Contact._meta.get_field(f).verbose_name
                                                                    for f in merging.FILLABLE}})
