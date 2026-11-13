from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from crm.contacts.models import Contact
from crm.core import clock
from crm.core.db import parse_version
from crm.core.errors import DomainError
from crm.core.web import new_operation_id, paginate, run_action, safe_next

from . import services
from .forms import HandoverForm, ReplanForm, TaskForm
from .models import Assignment, Handover, Pool, Task

User = get_user_model()


def shared_work(request):
    pools = []
    for pool in Pool.objects.filter(active=True).select_related("coordinator", "backup_coordinator"):
        waiting = (Assignment.objects.filter(kind="pool", pool=pool).select_related("contact")
                   .order_by("since"))
        pools.append({"pool": pool, "waiting": waiting[:50], "count": waiting.count()})
    pending = Handover.objects.filter(state="requested").select_related("contact", "sender", "recipient", "pool__coordinator",
                                                                        "pool__backup_coordinator").order_by("requested_at")
    mine_to_decide = [h for h in pending if services.can_decide(h, request.user)]
    mine_sent = [h for h in pending if h.sender_id == request.user.pk]
    recent = Handover.objects.exclude(state="requested").select_related("contact", "sender", "recipient", "pool", "decided_by")[:15]
    return render(request, "work/shared.html", {
        "pools": pools, "pending": pending, "to_decide": mine_to_decide, "sent": mine_sent, "recent": recent,
        "operation_id": new_operation_id(), "now": clock.now(),
    })


@require_POST
def claim(request, contact_id):
    contact = get_object_or_404(Contact, pk=contact_id)
    version = parse_version(request.POST.get("version", ""))
    if version is None:
        messages.error(request, "Missing assignment version; reload the page.")
        return redirect(safe_next(request, "/work/shared/"))
    response, result = run_action(
        request,
        lambda: services.claim(contact, actor=request.user, expected_version=version,
                               operation_id=request.POST.get("operation_id", "")),
        success="", redirect_to=safe_next(request, f"/contacts/{contact.pk}/"),
    )
    if result is not None:
        messages.success(request, f"You are now responsible for {contact.display_name}." if not result.replayed
                         else "Claim already recorded.")
    return response


def handover_new(request, contact_id):
    contact = get_object_or_404(Contact, pk=contact_id)
    assignment = Assignment.objects.select_related("user", "pool").get(contact=contact)
    if not services.can_initiate_handover(assignment, request.user):
        messages.error(request, "Only the current handler (or the pool coordinator for pool-held clients) can request a handover.")
        return redirect("contacts:detail", pk=contact.pk)
    open_tasks = list(Task.objects.filter(contact=contact, status="open").select_related("assignee").order_by("due_at"))
    form = HandoverForm(request.POST or None, tasks=open_tasks, initial={"version": assignment.version},
                        exclude_user=assignment.user if assignment.kind == "person" else None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            services.request_handover(contact, actor=request.user, kind=d["kind"], recipient=d.get("recipient"),
                                      pool=d.get("pool"), reason=d["reason"], context=d["context"],
                                      task_dispositions=form.dispositions(), expected_version=d["version"])
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            messages.success(request, "Handover requested. You remain responsible until it is accepted.")
            return redirect("contacts:detail", pk=contact.pk)
    return render(request, "work/handover_new.html", {"form": form, "contact": contact, "assignment": assignment,
                                                      "open_tasks": open_tasks})


@require_POST
def handover_decide(request, pk, decision):
    handover = get_object_or_404(Handover, pk=pk)
    note = request.POST.get("note", "")
    actions = {
        "accept": (lambda: services.accept_handover(handover, actor=request.user), "Accepted. You are now responsible."),
        "decline": (lambda: services.decline_handover(handover, actor=request.user, note=note),
                    "Declined. The sender remains responsible."),
        "cancel": (lambda: services.cancel_handover(handover, actor=request.user, note=note), "Handover cancelled."),
    }
    if decision not in actions:
        messages.error(request, "Unknown action.")
        return redirect("work:shared")
    fn, success = actions[decision]
    response, _ = run_action(request, fn, success=success, redirect_to=safe_next(request, "/work/shared/"))
    return response


def tasks(request):
    now = clock.now()
    scope = request.GET.get("scope", "mine")
    status = request.GET.get("status", "open")
    qs = Task.objects.select_related("contact", "assignee").order_by("due_at", "id")
    if scope == "mine":
        qs = qs.filter(assignee=request.user)
    elif scope.isdigit():
        qs = qs.filter(assignee_id=int(scope))
    if status == "open":
        qs = qs.filter(status="open")
    elif status == "overdue":
        qs = qs.filter(status="open", due_at__lt=now)
    elif status == "done":
        qs = qs.filter(status__in=("done", "cancelled")).order_by("-completed_at")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(contact__display_name__icontains=q))
    page, querystring = paginate(request, qs, per_page=30)
    return render(request, "work/tasks.html", {
        "page": page, "querystring": querystring, "scope": scope, "status": status, "q": q, "now": now,
        "users": User.objects.filter(is_active=True).order_by("full_name"),
    })


@require_POST
def task_create(request, contact_id):
    from crm.contacts.views import render_detail

    contact = get_object_or_404(Contact, pk=contact_id)
    form = TaskForm(request.POST, prefix="task")
    if not form.is_valid():
        return render_detail(request, contact, task_form=form, status=400)
    d = form.cleaned_data
    try:
        services.create_task(contact, actor=request.user, assignee=d["assignee"], title=d["title"], kind=d["kind"],
                             due_at=d["due_at"], description=d["description"], critical=d["critical"])
    except DomainError as exc:
        form.add_error(None, exc.message)
        return render_detail(request, contact, task_form=form, status=400)
    messages.success(request, "Next action created.")
    return redirect("contacts:detail", pk=contact.pk)


def _version(request):
    parsed = parse_version(request.POST.get("version", ""))
    return parsed if parsed is not None else -1


@require_POST
def task_complete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    response, _ = run_action(request, lambda: services.complete_task(task, actor=request.user, note=request.POST.get("note", ""),
                                                                     expected_version=_version(request)),
                             success="Task completed.", redirect_to=safe_next(request, f"/contacts/{task.contact_id}/"))
    return response


@require_POST
def task_cancel(request, pk):
    task = get_object_or_404(Task, pk=pk)
    response, _ = run_action(request, lambda: services.cancel_task(task, actor=request.user, reason=request.POST.get("reason", ""),
                                                                   expected_version=_version(request)),
                             success="Task cancelled.", redirect_to=safe_next(request, f"/contacts/{task.contact_id}/"))
    return response


def task_detail(request, pk):
    task = get_object_or_404(Task.objects.select_related("contact", "assignee", "created_by", "completed_by"), pk=pk)
    replan = ReplanForm(request.POST or None, initial={"due_at": task.due_at, "version": task.version})
    if request.method == "POST":
        if request.POST.get("action") == "reassign":
            assignee = User.objects.filter(pk=request.POST.get("assignee") or 0, is_active=True).first()
            response, _ = run_action(request, lambda: services.reassign_task(task, actor=request.user, assignee=assignee,
                                                                             expected_version=_version(request)),
                                     success="Task reassigned.", redirect_to=f"/work/tasks/{task.pk}/")
            return response
        if replan.is_valid():
            d = replan.cleaned_data
            try:
                services.replan_task(task, actor=request.user, due_at=d["due_at"], reason=d["reason"], expected_version=d["version"])
            except DomainError as exc:
                replan.add_error(None, exc.message)
            else:
                messages.success(request, "Due time changed; the original due time is kept in history.")
                return redirect("work:task", pk=task.pk)
    return render(request, "work/task.html", {"task": task, "replan": replan, "now": clock.now(),
                                              "users": User.objects.filter(is_active=True).order_by("full_name")})
