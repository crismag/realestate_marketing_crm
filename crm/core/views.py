from __future__ import annotations

import hashlib

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from crm.accounts.models import Team
from crm.attention import services as attention
from crm.automation.models import Notification
from crm.automation.worker import worker_health
from crm.contacts.models import Source
from crm.work.models import Handover, Pool, Task

from . import clock
from .errors import DomainError
from .models import AuditEvent, BrandLogo, SettingsVersion
from .services import audit, get_policy, get_settings_row, update_policy
from .settings_forms import CompanyForm, PolicyForm, PoolForm, SourceForm, TeamForm
from .web import paginate

User = get_user_model()


def csrf_failure(request, reason=""):
    return render(request, "errors/403_csrf.html", status=403)


def not_found(request, exception=None):
    return render(request, "errors/404.html", status=404)


def server_error(request):
    return render(request, "errors/500.html", status=500)


def permission_denied(request, exception=None):
    return render(request, "errors/403.html", {"reason": str(exception) if exception else ""}, status=403)


@login_not_required
def healthz(request):
    """Liveness/readiness without disclosing data: database reachable + worker heartbeat recency."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    health = worker_health() if db_ok else {"alive": False}
    return JsonResponse({"database": "ok" if db_ok else "unavailable", "worker_alive": health.get("alive", False)},
                        status=200 if db_ok else 503)


def today(request):
    policy = get_policy()
    now = clock.now()
    items = attention.evaluate(now=now, policy=policy)
    mine = attention.filter_items(items, user=request.user, scope="mine")
    summary = attention.summarize(mine)
    team_summary = attention.summarize(items)
    my_tasks = Task.objects.filter(assignee=request.user, status="open").select_related("contact").order_by("due_at")[:15]
    to_decide = [h for h in Handover.objects.filter(state="requested").select_related("contact", "sender", "recipient", "pool")
                 if (h.kind == "transfer" and h.recipient_id == request.user.pk)
                 or (h.kind == "release" and request.user in h.pool.accountable_users())]
    sent = Handover.objects.filter(state="requested", sender=request.user).select_related("contact", "recipient", "pool")
    coverage = attention.coverage(now=now, policy=policy, user=request.user)
    notes = Notification.objects.filter(recipient=request.user, dismissed_at__isnull=True).select_related("contact")[:6]
    return render(request, "core/today.html", {
        "items": mine[:25], "mine_total": len(mine), "summary": summary, "team_summary": team_summary,
        "reasons": attention.REASONS, "my_tasks": my_tasks, "to_decide": to_decide, "sent": sent, "coverage": coverage,
        "notes": notes, "now": now, "health": worker_health(now),
        "setup": setup_steps(policy) if request.user.is_staff else None,
    })


def setup_steps(policy) -> dict | None:
    """First-run checklist for a new company install. Derived from data, nothing is stored; None when complete."""
    from crm.contacts.models import Contact

    from .policy import DEFAULT_POLICY

    company = policy.get("company") or {}
    steps = [
        ("Fill in the company profile and logo", "core:company",
         policy["workspace_name"] != DEFAULT_POLICY["workspace_name"] or any(company.values())),
        ("Review timezone, currency, stages and follow-up timings", "core:settings",
         bool(policy.get("setup", {}).get("settings_reviewed"))),
        ("Add your agents and coordinators", "accounts:users",
         get_user_model().objects.filter(is_active=True).count() > 1),
        ("Create a shared pool with a coordinator", "core:pool_new",
         Pool.objects.filter(active=True, coordinator__isnull=False).exists()),
        ("Capture or import your first contacts", "contacts:new", Contact.objects.exists()),
    ]
    done = sum(1 for *_, ok in steps if ok)
    if done == len(steps):
        return None
    return {"steps": [{"label": label, "url": url, "done": ok} for label, url, ok in steps], "done": done,
            "total": len(steps)}


def _require_admin_for_writes(request):
    """Everyone may read workspace configuration; only administrators may change it."""
    if request.method not in ("GET", "HEAD") and not request.user.is_staff:
        raise PermissionDenied("Only workspace administrators can change settings.")


def settings_index(request):
    _require_admin_for_writes(request)
    row = get_settings_row()
    policy = get_policy()
    form = PolicyForm(request.POST or None, initial=PolicyForm.initial_from(policy, row.version))
    if request.method == "POST" and form.is_valid():
        try:
            update_policy(form.to_policy(policy), actor=request.user, expected_version=form.cleaned_data["version"],
                          note=form.cleaned_data["note"])
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            messages.success(request, "Settings saved as a new version. Current queues use the new values now; history is unchanged.")
            return redirect("core:settings")
    return render(request, "core/settings.html", {
        "form": form, "row": row, "versions": SettingsVersion.objects.select_related("changed_by")[:10],
        "pools": Pool.objects.select_related("coordinator", "backup_coordinator", "team"),
        "teams": Team.objects.all(), "sources": Source.objects.all(),
    })


def _simple_edit(request, *, model, form_class, pk, fields, label, redirect_to="core:settings", template="core/simple_form.html"):
    if not request.user.is_staff:
        raise PermissionDenied("Only workspace administrators can change settings.")
    obj = get_object_or_404(model, pk=pk) if pk else None
    initial = {f: getattr(obj, f) for f in fields} if obj else {}
    form = form_class(request.POST or None, initial=initial)
    if obj is not None and "code" in form.fields:
        form.fields["code"].disabled = True
    if request.method == "POST" and form.is_valid():
        data = {f: form.cleaned_data[f] for f in fields if not (obj is not None and f == "code")}
        try:
            with transaction.atomic():
                if obj is None:
                    obj = model.objects.create(**data)
                    action = "created"
                else:
                    model.objects.filter(pk=obj.pk).update(**data)
                    action = "updated"
                audit(f"{model.__name__.lower()}.{action}", obj, f"{label} '{data.get('name') or data.get('label') or obj}' {action}",
                      actor=request.user)
        except Exception as exc:  # noqa: BLE001 - unique constraint etc. shown to the user
            if "UNIQUE" in str(exc).upper():
                form.add_error(None, "That name or code is already used.")
            else:
                raise
        else:
            messages.success(request, f"{label} saved.")
            return redirect(redirect_to)
    return render(request, template, {"form": form, "title": f"{'Edit' if obj else 'Add'} {label.lower()}", "obj": obj})


def pool_edit(request, pk=None):
    return _simple_edit(request, model=Pool, form_class=PoolForm, pk=pk,
                        fields=["name", "team", "coordinator", "backup_coordinator", "active"], label="Pool")


def team_edit(request, pk=None):
    return _simple_edit(request, model=Team, form_class=TeamForm, pk=pk, fields=["name", "active"], label="Team")


def source_edit(request, pk=None):
    return _simple_edit(request, model=Source, form_class=SourceForm, pk=pk, fields=["code", "label", "kind", "active"],
                        label="Source")


def audit_log(request):
    qs = AuditEvent.objects.select_related("actor", "contact")
    action = request.GET.get("action", "").strip()
    if action:
        qs = qs.filter(action__startswith=action)
    actor = request.GET.get("actor", "")
    if actor.isdigit():
        qs = qs.filter(actor_id=int(actor))
    page, querystring = paginate(request, qs, per_page=50)
    return render(request, "core/audit.html", {"page": page, "querystring": querystring, "action": action, "actor": actor,
                                               "users": User.objects.order_by("full_name")})


def company_profile(request):
    _require_admin_for_writes(request)
    row = get_settings_row()
    policy = get_policy()
    form = CompanyForm(request.POST or None, request.FILES or None, initial=CompanyForm.initial_from(policy, row.version))
    logo = BrandLogo.objects.filter(pk=1).only("sha256", "uploaded_at").first()
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            with transaction.atomic():
                update_policy(form.to_policy(policy), actor=request.user, expected_version=d["version"],
                              note=d["note"] or "Company profile")
                if d["logo"]:
                    digest = hashlib.sha256(d["logo"]["data"]).hexdigest()
                    BrandLogo.objects.update_or_create(pk=1, defaults={
                        "data": d["logo"]["data"], "content_type": d["logo"]["content_type"], "sha256": digest,
                        "uploaded_at": clock.now(), "uploaded_by": request.user})
                    audit("brand.logo_uploaded", get_settings_row(), f"Logo uploaded ({len(d['logo']['data'])} bytes)",
                          actor=request.user, data={"sha256": digest})
                elif d["remove_logo"] and logo is not None:
                    BrandLogo.objects.filter(pk=1).delete()
                    audit("brand.logo_removed", get_settings_row(), "Logo removed", actor=request.user)
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            messages.success(request, "Company profile saved.")
            return redirect("core:company")
    return render(request, "core/company.html", {"form": form, "logo": logo})


@login_not_required
def brand_logo(request):
    logo = BrandLogo.objects.filter(pk=1).first()
    if logo is None:
        raise Http404("No logo")
    etag = f'"{logo.sha256}"'
    if request.headers.get("If-None-Match") == etag:
        response = HttpResponse(status=304)
    else:
        response = HttpResponse(bytes(logo.data), content_type=logo.content_type)
    response["ETag"] = etag
    response["Cache-Control"] = "public, max-age=300"
    response["X-Content-Type-Options"] = "nosniff"
    return response
