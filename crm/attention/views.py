import datetime as dt

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from crm.accounts.models import Team
from crm.contacts.models import Contact
from crm.core import clock
from crm.core.db import parse_version
from crm.core.errors import DomainError
from crm.core.services import get_policy
from crm.core.web import safe_next
from crm.work.models import Pool

from . import services

User = get_user_model()

_SNOOZE_DAYS = {1, 3, 7, 14, 30}


def _optional_id(raw: str):
    """An omitted filter is None. A nonempty value that is not a version is refused."""
    if raw == "":
        return None, False
    parsed = parse_version(raw)
    return parsed, parsed is None


def queue(request):
    policy = get_policy()
    now = clock.now()
    scope = request.GET.get("scope", "mine")
    reason = request.GET.get("reason", "")
    include_snoozed = request.GET.get("snoozed") == "1"
    pool_id, pool_invalid = _optional_id(request.GET.get("pool", ""))
    team_id, team_invalid = _optional_id(request.GET.get("team", ""))
    person_id, person_invalid = _optional_id(request.GET.get("person", ""))
    if pool_invalid or team_invalid or person_invalid:
        messages.error(request, "That person, team, or pool filter is not valid.")
        return render(request, "attention/queue.html", {
            "items": [], "total": 0, "summary": {"unique_contacts": 0, "per_reason": {}}, "reasons": services.REASONS,
            "scope": scope, "reason": reason, "include_snoozed": include_snoozed, "now": now, "person": "",
            "pools": Pool.objects.filter(active=True), "teams": Team.objects.filter(active=True), "pool_id": None,
            "team_id": None, "users": User.objects.filter(is_active=True).order_by("full_name"),
            "evaluated_at": now,
        }, status=400)
    items = services.evaluate(now=now, policy=policy)
    if person_id is not None:
        target = User.objects.filter(pk=person_id).first()
        filtered = services.filter_items(items, user=target, scope="mine", reason=reason, include_snoozed=include_snoozed,
                                         pool_id=pool_id, team_id=team_id)
    else:
        filtered = services.filter_items(items, user=request.user, scope=scope, reason=reason, include_snoozed=include_snoozed,
                                         pool_id=pool_id, team_id=team_id)
    summary = services.summarize(services.filter_items(items, user=request.user, scope=scope if person_id is None else "all",
                                                       pool_id=pool_id, team_id=team_id))
    return render(request, "attention/queue.html", {
        "items": filtered[:300], "total": len(filtered), "summary": summary, "reasons": services.REASONS,
        "scope": scope, "reason": reason, "include_snoozed": include_snoozed, "now": now,
        "person": str(person_id) if person_id is not None else "",
        "pools": Pool.objects.filter(active=True), "teams": Team.objects.filter(active=True), "pool_id": pool_id,
        "team_id": team_id, "users": User.objects.filter(is_active=True).order_by("full_name"),
        "evaluated_at": now,
    })


@require_POST
def snooze(request, contact_id):
    contact = get_object_or_404(Contact, pk=contact_id)
    reason_code = request.POST.get("reason_code", "")
    raw_days = request.POST.get("days", "")
    if raw_days not in {str(n) for n in _SNOOZE_DAYS}:
        messages.error(request, "Choose 1, 3, 7, 14, or 30 days.")
        return redirect(safe_next(request, f"/contacts/{contact.pk}/"))
    days = int(raw_days)
    until = clock.now() + dt.timedelta(days=days)
    try:
        services.snooze(contact, actor=request.user, reason_code=reason_code, until=until, note=request.POST.get("note", ""))
    except DomainError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, f"Snoozed for {days} day(s). The reminder resurfaces after that; history is unchanged.")
    return redirect(safe_next(request, f"/contacts/{contact.pk}/"))


@require_POST
def unsnooze(request, contact_id):
    contact = get_object_or_404(Contact, pk=contact_id)
    services.clear_snooze(contact, actor=request.user, reason_code=request.POST.get("reason_code", ""))
    messages.success(request, "Snooze cleared.")
    return redirect(safe_next(request, f"/contacts/{contact.pk}/"))
