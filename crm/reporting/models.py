from __future__ import annotations

from django.conf import settings
from django.db import models

from crm.core import clock


class SpendEntry(models.Model):
    """Manually entered marketing spend in integer minor units."""

    KINDS = [("actual", "Actual"), ("planned", "Planned")]
    source = models.ForeignKey("contacts.Source", on_delete=models.PROTECT, related_name="spend_entries")
    kind = models.CharField(max_length=10, choices=KINDS, default="actual")
    period_start = models.DateField()
    period_end = models.DateField()
    amount_minor = models.BigIntegerField()
    currency = models.CharField(max_length=3)
    note = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(default=clock.now)

    class Meta:
        ordering = ["-period_start"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount_minor__gte=0), name="spend_nonnegative"),
            models.CheckConstraint(condition=models.Q(period_end__gte=models.F("period_start")), name="spend_period_order"),
        ]
