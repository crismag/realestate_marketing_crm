"""Transactional writes for marketing reporting inputs."""
from crm.core.db import write_transaction
from crm.core.services import audit

from .models import SpendEntry


def create_spend(*, actor, source, kind, period_start, period_end, amount_minor, currency, note=""):
    """Persist spend and its audit evidence together, or neither."""
    def run():
        entry = SpendEntry.objects.create(source=source, kind=kind, period_start=period_start, period_end=period_end,
                                          amount_minor=amount_minor, currency=currency, note=note, created_by=actor)
        audit("spend.created", entry, f"{kind} spend recorded for {source}", actor=actor)
        return entry

    return write_transaction(run)
