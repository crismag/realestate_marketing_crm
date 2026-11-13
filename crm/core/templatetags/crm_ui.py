"""Template helpers that render CrisGen UI component markup consistently."""
from __future__ import annotations

from django import template
from django.utils import timezone
from django.utils.html import format_html

from crm.core import clock

register = template.Library()

STATUS_COLORS = {
    # chip colour per status/reason; None = neutral chip
    "succeeded": "success", "sandbox_captured": "secondary", "delivered": "success", "accepted": "success",
    "done": "success", "responded": "success", "won": "success", "running": "secondary", "queued": "secondary",
    "scheduled": "secondary", "requested": "warning", "failed": "error", "dead": "error", "uncertain": "warning",
    "routing_gap": "error", "declined": None, "cancelled": None, "stale": None, "suppressed": None, "lost": None,
    "open": "secondary", "awaiting": "warning", "closed": None,
    "inquiry_awaiting": "warning", "task_overdue": "error", "promise_due": "error", "toured_no_followup": "warning",
    "inactive": "warning", "opportunity_stalled": "warning", "next_action_missing": "secondary", "pool_waiting": "secondary",
    "handover_waiting": "warning", "critical_task": "error",
}


@register.simple_tag
def chip(label, status=None, variant="ghost"):
    color = STATUS_COLORS.get(status, None) if status is not None else None
    if color is None:
        return format_html('<span class="chip-neutral">{}</span>', label)
    return format_html(
        '<span class="cg-chip" data-variant="{}" data-color="{}" data-size="sm"><span class="cg-chip__label">{}</span></span>',
        variant, color, label,
    )


@register.simple_tag(takes_context=True)
def nav_current(context, prefix):
    path = context["request"].path
    if prefix == "/":
        return "page" if path == "/" else ""
    return "page" if path.startswith(prefix) else ""


@register.filter
def ago(value):
    if not value:
        return "never"
    seconds = (clock.now() - value).total_seconds()
    future = seconds < 0
    seconds = abs(seconds)
    if seconds < 3600:
        text = f"{int(seconds // 60)} min"
    elif seconds < 86400 * 2:
        text = f"{int(seconds // 3600)} h"
    else:
        text = f"{int(seconds // 86400)} days"
    return f"in {text}" if future else f"{text} ago"


@register.filter
def local(value, fmt="Y-m-d H:i"):
    from django.utils.dateformat import format as dformat

    if not value:
        return ""
    return dformat(timezone.localtime(value), fmt)


@register.filter
def money(minor, currency=""):
    if minor is None:
        return "—"
    sign = "-" if minor < 0 else ""
    minor = abs(int(minor))
    return f"{sign}{currency + ' ' if currency else ''}{minor // 100:,}.{minor % 100:02d}"


@register.filter
def pct(ratio):
    if ratio is None:
        return "n/a"
    return f"{ratio * 100:.0f}%"


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None
