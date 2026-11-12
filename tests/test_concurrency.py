"""Concurrency-sensitive rules with real threads and separate SQLite connections."""
import threading
import uuid

import pytest
from django.db import connection

from crm.core.errors import ConflictError, ServiceUnavailable
from crm.work import services as work
from crm.work.models import Assignment, AssignmentEvent

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.concurrency]


def _race(fns):
    barrier = threading.Barrier(len(fns))
    results = [None] * len(fns)

    def runner(i, fn):
        try:
            barrier.wait()
            results[i] = ("ok", fn())
        except Exception as exc:  # noqa: BLE001
            results[i] = ("err", exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=runner, args=(i, fn)) for i, fn in enumerate(fns)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return results


def test_simultaneous_claims_have_exactly_one_winner(users, pool, make_contact):
    for _ in range(5):
        c = make_contact(destination="pool", pool=pool)
        v = Assignment.objects.get(contact=c).version
        claimers = [users["ana"], users["ben"], users["max"], users["cora"]]
        results = _race([lambda u=u, c=c, v=v: work.claim(c, actor=u, expected_version=v, operation_id=uuid.uuid4().hex)
                         for u in claimers])
        winners = [r for r in results if r[0] == "ok"]
        losers = [r for r in results if r[0] == "err"]
        assert len(winners) == 1, results
        assert all(isinstance(e, (ConflictError, ServiceUnavailable)) for _, e in losers), losers
        assert AssignmentEvent.objects.filter(contact=c, event_type="claimed").count() == 1
        a = Assignment.objects.get(contact=c)
        assert a.kind == "person" and a.version == v + 1


def test_simultaneous_accepts_of_same_handover_transfer_once(users, make_contact):
    c = make_contact()
    h = work.request_handover(c, actor=users["ana"], kind="transfer", recipient=users["ben"], reason="r", expected_version=1)
    results = _race([lambda: work.accept_handover(h, actor=users["ben"]) for _ in range(3)])
    assert sum(1 for r in results if r[0] == "ok") >= 1
    assert AssignmentEvent.objects.filter(contact=c, event_type="handover_accepted").count() == 1
    assert Assignment.objects.get(contact=c).version == 2


def test_claim_racing_a_release_acceptance_never_double_assigns(users, pool, make_contact):
    c = make_contact(destination="pool", pool=pool)
    h = work.request_handover(c, actor=users["cora"], kind="transfer", recipient=users["ana"], reason="r", expected_version=1)
    results = _race([
        lambda: work.claim(c, actor=users["ben"], expected_version=1, operation_id=uuid.uuid4().hex),
        lambda: work.accept_handover(h, actor=users["ana"]),
    ])
    assert sum(1 for r in results if r[0] == "ok") == 1, results
    a = Assignment.objects.get(contact=c)
    assert a.version == 2 and a.kind == "person"
