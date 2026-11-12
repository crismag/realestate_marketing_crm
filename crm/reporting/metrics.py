"""Declared metric definitions (context METRIC_DICTIONARY.md). Every number on a report comes from
one of these functions, and its drill-down lists exactly the records the function counted."""
from __future__ import annotations

import datetime as dt
import statistics
import zoneinfo
from dataclasses import dataclass

from django.db.models import QuerySet

from crm.contacts.models import Contact, Inquiry, Interaction, Opportunity

from .models import SpendEntry

DEFINITIONS_VERSION = "2026-11-13.1"
DEFINITIONS = {
    "acquisitions": ("Acquisitions", "Contacts captured (created) in the period, by acquisition source. Staff-entered "
                     "contacts are not signups. Archived contacts still count; duplicates are only merged by people."),
    "inquiries": ("Inquiries", "Inquiries received in the period (repeat inquiries from the same person count separately)."),
    "won_count": ("Opportunities won", "Opportunities whose outcome is Won with a close time in the period."),
    "won_value": ("Won value", "Sum of won opportunity amounts closed in the period, in the workspace currency. "
                  "Not cash received and not earnings."),
    "spend": ("Actual spend", "Sum of actual spend entries whose whole period lies inside the report period. Entries that "
              "only partly overlap are listed as excluded, not prorated."),
    "cost_per_acquisition": ("Cost per acquisition", "Actual spend / acquisitions for the same source and period. "
                             "Not applicable when either is missing or zero, or currencies differ."),
    "earnings": ("Earnings", "Unavailable: no recognised-revenue or commission data source is configured (OQ-011)."),
    "response_time": ("Inquiry response time", "Hours from inquiry receipt to the first linked personal response, for "
                      "inquiries received in the period that were responded to. Automated emails do not count."),
    "activity": ("Logged activity", "Interactions logged in the period by type. Volume is not a measure of sales quality."),
}


@dataclass
class Period:
    start: dt.datetime
    end: dt.datetime  # exclusive
    tz: zoneinfo.ZoneInfo
    start_date: dt.date
    end_date: dt.date  # inclusive, for display

    @classmethod
    def from_dates(cls, start: dt.date, end: dt.date, tz_name: str) -> Period:
        tz = zoneinfo.ZoneInfo(tz_name)
        s = dt.datetime.combine(start, dt.time.min, tzinfo=tz)
        e = dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, tzinfo=tz)
        return cls(s.astimezone(dt.UTC), e.astimezone(dt.UTC), tz, start, end)


def acquisitions(period: Period, source_id: int | None = None) -> QuerySet:
    qs = Contact.objects.filter(created_at__gte=period.start, created_at__lt=period.end)
    return qs.filter(source_id=source_id) if source_id else qs


def inquiries(period: Period, source_id: int | None = None) -> QuerySet:
    qs = Inquiry.objects.filter(received_at__gte=period.start, received_at__lt=period.end)
    return qs.filter(source_id=source_id) if source_id else qs


def won(period: Period, source_id: int | None = None) -> QuerySet:
    qs = Opportunity.objects.filter(outcome="won", closed_at__gte=period.start, closed_at__lt=period.end)
    return qs.filter(contact__source_id=source_id) if source_id else qs


def spend_entries(period: Period, source_id: int | None = None) -> tuple[QuerySet, QuerySet]:
    base = SpendEntry.objects.filter(kind="actual")
    if source_id:
        base = base.filter(source_id=source_id)
    inside = base.filter(period_start__gte=period.start_date, period_end__lte=period.end_date)
    partial = base.filter(period_start__lte=period.end_date, period_end__gte=period.start_date).exclude(
        pk__in=inside.values("pk"))
    return inside, partial


def money_sum(rows, currency: str) -> tuple[int | None, list[str]]:
    total, other = 0, set()
    found = False
    for amount, cur in rows:
        if amount is None:
            continue
        if cur and cur != currency:
            other.add(cur)
            continue
        total += amount
        found = True
    return (total if found else None), sorted(other)


def response_hours(period: Period) -> dict:
    responded = inquiries(period).filter(status="responded", responded_at__isnull=False)
    hours = [(i.responded_at - i.received_at).total_seconds() / 3600 for i in responded]
    awaiting = inquiries(period).filter(status="awaiting").count()
    return {
        "responded": len(hours),
        "awaiting": awaiting,
        "median_hours": statistics.median(hours) if hours else None,
        "ids": [i.pk for i in responded],
    }


def activity(period: Period) -> QuerySet:
    return Interaction.objects.filter(occurred_at__gte=period.start, occurred_at__lt=period.end)
