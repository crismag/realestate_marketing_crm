from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import redirect, render

from crm.attention import services as attention
from crm.contacts.models import Contact, Inquiry, Source
from crm.core import clock
from crm.core.errors import DomainError
from crm.core.forms import Form
from crm.core.services import get_policy
from crm.work.models import Assignment, Task

from . import metrics, services
from .models import SpendEntry

User = get_user_model()


def _period(request, policy):
    today = clock.now().astimezone(metrics.Period.from_dates(dt.date.today(), dt.date.today(), policy["timezone"]).tz).date()
    try:
        start = dt.date.fromisoformat(request.GET.get("from", ""))
    except ValueError:
        start = today - dt.timedelta(days=29)
    try:
        end = dt.date.fromisoformat(request.GET.get("to", ""))
    except ValueError:
        end = today
    if end < start:
        start, end = end, start
    return metrics.Period.from_dates(start, end, policy["timezone"])


def index(request):
    policy = get_policy()
    now = clock.now()
    period = _period(request, policy)
    currency = policy["currency"]
    items = attention.evaluate(now=now, policy=policy)

    people = []
    for user in User.objects.filter(is_active=True).order_by("full_name"):
        mine = attention.filter_items(items, user=user, scope="mine")
        summary = attention.summarize(mine)
        cov = attention.coverage(now=now, policy=policy, user=user)
        people.append({
            "user": user,
            "assigned": Assignment.objects.filter(kind="person", user=user, contact__archived_at__isnull=True,
                                                  contact__disposition__in=("active", "nurture")).count(),
            "needing": summary["unique_contacts"], "per_reason": summary["per_reason"],
            "open_tasks": Task.objects.filter(assignee=user, status="open").count(),
            "overdue": Task.objects.filter(assignee=user, status="open", due_at__lt=now).count(),
            "done_in_period": Task.objects.filter(assignee=user, status="done", completed_at__gte=period.start,
                                                  completed_at__lt=period.end).count(),
            "coverage": cov,
        })

    sources = []
    for source in list(Source.objects.all()) + [None]:
        sid = source.pk if source else None
        acq = metrics.acquisitions(period).filter(source__isnull=True) if source is None else metrics.acquisitions(period, sid)
        inq = metrics.inquiries(period).filter(source__isnull=True) if source is None else metrics.inquiries(period, sid)
        won = metrics.won(period).filter(contact__source__isnull=True) if source is None else metrics.won(period, sid)
        won_value, won_other = metrics.money_sum(won.values_list("amount_minor", "currency"), currency)
        if source is not None:
            inside, partial = metrics.spend_entries(period, sid)
            spend, spend_other = metrics.money_sum(inside.values_list("amount_minor", "currency"), currency)
            partial_count = partial.count()
        else:
            spend, spend_other, partial_count = None, [], 0
        acq_count = acq.count()
        cpa = None
        if spend is not None and acq_count and not spend_other:
            cpa = int(Decimal(spend) / acq_count)
        row = {"source": source, "acquisitions": acq_count, "inquiries": inq.count(), "won": won.count(),
               "won_value": won_value, "won_other": won_other, "spend": spend, "spend_other": spend_other,
               "partial": partial_count, "cpa": cpa}
        if source is None and not any((row["acquisitions"], row["inquiries"], row["won"])):
            continue
        sources.append(row)

    activity = metrics.activity(period).values("kind").annotate(n=Count("id")).order_by("kind")
    activity_by_user = (metrics.activity(period).values("actor__full_name", "kind").annotate(n=Count("id"))
                        .order_by("actor__full_name", "kind"))
    response = metrics.response_hours(period)
    team = attention.summarize(items)
    return render(request, "reporting/index.html", {
        "period": period, "currency": currency, "people": people, "sources": sources, "activity": activity,
        "activity_by_user": activity_by_user, "response": response, "team": team, "reasons": attention.REASONS,
        "definitions": metrics.DEFINITIONS, "definitions_version": metrics.DEFINITIONS_VERSION, "generated_at": now,
        "policy_tz": policy["timezone"],
        "lifecycle_counts": Contact.objects.filter(archived_at__isnull=True).values("lifecycle").annotate(n=Count("id")),
        "query": request.GET.urlencode(),
    })


def drill(request):
    """Lists exactly the records behind a report number."""
    policy = get_policy()
    period = _period(request, policy)
    metric = request.GET.get("metric", "")
    source = request.GET.get("source", "")
    sid = int(source) if source.isdigit() else None
    none_source = source == "none"
    title, rows, kind = "", [], "contacts"
    if metric == "acquisitions":
        qs = metrics.acquisitions(period, sid)
        qs = qs.filter(source__isnull=True) if none_source else qs
        title, rows = "Acquisitions", qs.select_related("source", "assignment__user", "assignment__pool")
    elif metric == "inquiries":
        qs = metrics.inquiries(period, sid)
        qs = qs.filter(source__isnull=True) if none_source else qs
        title, rows, kind = "Inquiries", qs.select_related("contact", "source"), "inquiries"
    elif metric == "won":
        qs = metrics.won(period, sid)
        qs = qs.filter(contact__source__isnull=True) if none_source else qs
        title, rows, kind = "Won opportunities", qs.select_related("contact"), "opportunities"
    elif metric == "spend":
        inside, partial = metrics.spend_entries(period, sid)
        title, rows, kind = "Spend entries", list(inside.select_related("source")), "spend"
        return render(request, "reporting/drill.html", {"title": title, "rows": rows, "kind": kind, "period": period,
                                                        "partial": partial.select_related("source"),
                                                        "definition": metrics.DEFINITIONS["spend"],
                                                        "currency": policy["currency"]})
    elif metric == "responded":
        ids = metrics.response_hours(period)["ids"]
        title, rows, kind = "Responded inquiries", Inquiry.objects.filter(pk__in=ids).select_related("contact"), "inquiries"
    else:
        messages.error(request, "Unknown metric.")
        return redirect("reporting:index")
    return render(request, "reporting/drill.html", {"title": title, "rows": rows, "kind": kind, "period": period,
                                                    "definition": metrics.DEFINITIONS.get(metric, ("", ""))
                                                    if metric != "won" else metrics.DEFINITIONS["won_count"],
                                                    "currency": policy["currency"]})


class SpendForm(Form):
    source = forms.ModelChoiceField(queryset=Source.objects.filter(active=True))
    kind = forms.ChoiceField(choices=SpendEntry.KINDS, initial="actual")
    period_start = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    period_end = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    amount = forms.DecimalField(min_value=0, max_digits=14, decimal_places=2)
    note = forms.CharField(max_length=200, required=False)

    def clean(self):
        data = super().clean()
        if data.get("period_start") and data.get("period_end") and data["period_end"] < data["period_start"]:
            self.add_error("period_end", "End must not be before start.")
        return data


def spend(request):
    policy = get_policy()
    form = SpendForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            services.create_spend(actor=request.user, source=d["source"], kind=d["kind"], period_start=d["period_start"],
                                  period_end=d["period_end"], amount_minor=int((d["amount"] * 100).quantize(Decimal("1"))),
                                  currency=policy["currency"], note=d["note"])
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            messages.success(request, "Spend recorded.")
            return redirect("reporting:spend")
    return render(request, "reporting/spend.html", {"form": form, "entries": SpendEntry.objects.select_related("source", "created_by")[:100],
                                                    "currency": policy["currency"]})
