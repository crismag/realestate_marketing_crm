from __future__ import annotations

from django import forms
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from crm.core import clock
from crm.core.forms import Form
from crm.core.services import audit, get_policy
from crm.core.web import paginate, run_action, safe_next

from . import engine
from .models import Job, Notification, Rule, RuleRun, RuleVersion
from .worker import cancel_job, retry_job, worker_health


def index(request):
    now = clock.now()
    rules = Rule.objects.all()
    last_runs = {}
    for run in RuleRun.objects.order_by("-started_at")[:200]:
        last_runs.setdefault(run.rule_id, run)
    return render(request, "automation/index.html", {
        "rules": rules, "last_runs": last_runs, "health": worker_health(now), "now": now,
        "gaps": Notification.objects.filter(status="routing_gap").select_related("contact", "rule")[:20],
        "failed_jobs": Job.objects.filter(status__in=("failed", "dead")).order_by("-updated_at")[:20],
    })


class RuleConfigForm(Form):
    enabled = forms.BooleanField(required=False)
    delay_minutes = forms.IntegerField(required=False, min_value=0, max_value=60 * 24 * 14,
                                       help_text="Customer rules only: wait this long after the trigger before sending")
    note = forms.CharField(max_length=200, label="Change note")
    version = forms.IntegerField(widget=forms.HiddenInput)


def rule_detail(request, key):
    rule = get_object_or_404(Rule, key=key)
    form = RuleConfigForm(request.POST or None, initial={"enabled": rule.enabled, "version": rule.version,
                                                          "delay_minutes": rule.config.get("delay_minutes")})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        config = dict(rule.config)
        if rule.audience == "customer" and d["delay_minutes"] is not None:
            config["delay_minutes"] = d["delay_minutes"]
        with transaction.atomic():
            updated = Rule.objects.filter(pk=rule.pk, version=d["version"]).update(
                enabled=d["enabled"], config=config, version=d["version"] + 1, updated_at=clock.now(), updated_by=request.user)
            if updated != 1:
                form.add_error(None, "This rule was changed by someone else. Reload and re-apply your change.")
            else:
                rule.refresh_from_db()
                RuleVersion.objects.create(rule=rule, version=rule.version, enabled=rule.enabled, config=config,
                                           changed_by=request.user, note=d["note"])
                audit("rule.updated", rule, f"Rule '{rule.name}' v{rule.version}: {'enabled' if rule.enabled else 'disabled'} ({d['note']})",
                      actor=request.user)
        if not form.errors:
            messages.success(request, f"Rule saved as version {rule.version}." + (
                "" if rule.enabled else " Disabled rules create no new actions; queued customer messages are cancelled at send time."))
            return redirect("automation:rule", key=key)
    preview = []
    if rule.key in engine.SWEEP_RULES:
        preview = [a for a in engine.planned_sweep_actions(clock.now(), get_policy()) if a["rule"] == rule.key][:50]
    return render(request, "automation/rule.html", {
        "rule": rule, "form": form, "versions": rule.versions.select_related("changed_by")[:10],
        "runs": rule.runs.all()[:15], "preview": preview,
        "recent": Notification.objects.filter(rule=rule).select_related("recipient", "contact")[:15],
    })


def jobs(request):
    qs = Job.objects.select_related("rule")
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)
    kind = request.GET.get("kind", "")
    if kind:
        qs = qs.filter(kind__startswith=kind)
    page, querystring = paginate(request, qs, per_page=40)
    return render(request, "automation/jobs.html", {"page": page, "querystring": querystring, "status": status, "kind": kind,
                                                    "statuses": Job.STATUSES, "health": worker_health()})


def job_detail(request, pk):
    job = get_object_or_404(Job.objects.select_related("rule"), pk=pk)
    return render(request, "automation/job.html", {"job": job, "attempts": job.attempt_log.all()})


@require_POST
def job_action(request, pk, action):
    job = get_object_or_404(Job, pk=pk)
    fn = {"retry": lambda: retry_job(job, actor=request.user), "cancel": lambda: cancel_job(job, actor=request.user)}.get(action)
    if fn is None:
        messages.error(request, "Unknown action.")
        return redirect("automation:job", pk=pk)
    response, _ = run_action(request, fn, success=f"Job {action} recorded. The worker processes it on its next pass.",
                             redirect_to=f"/automation/jobs/{pk}/")
    return response


def notifications(request):
    show = request.GET.get("show", "active")
    qs = Notification.objects.filter(recipient=request.user).select_related("contact", "task", "handover", "rule")
    if show == "active":
        qs = qs.filter(dismissed_at__isnull=True)
    elif show == "dismissed":
        qs = qs.filter(dismissed_at__isnull=False)
    page, querystring = paginate(request, qs, per_page=30)
    return render(request, "automation/notifications.html", {"page": page, "querystring": querystring, "show": show})


@require_POST
def notification_action(request, pk, action):
    note = get_object_or_404(Notification, pk=pk, recipient=request.user)
    now = clock.now()
    if action == "read":
        Notification.objects.filter(pk=note.pk, read_at__isnull=True).update(read_at=now)
    elif action == "dismiss":
        Notification.objects.filter(pk=note.pk).update(dismissed_at=now, read_at=note.read_at or now)
        messages.info(request, "Notification dismissed. The underlying task or reason is not completed by this.")
    elif action == "open":
        Notification.objects.filter(pk=note.pk, read_at__isnull=True).update(read_at=now)
        if note.contact_id:
            return redirect("contacts:detail", pk=note.contact_id)
    return redirect(safe_next(request, "/automation/notifications/"))


@require_POST
def notifications_read_all(request):
    count = Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=clock.now())
    messages.info(request, f"Marked {count} notification(s) as read.")
    return redirect("automation:notifications")
