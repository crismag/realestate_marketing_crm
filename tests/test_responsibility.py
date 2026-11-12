"""AT-001 / AT-002: exclusive claims and acceptance-based handovers (ADR-001, ADR-002)."""
import uuid

import pytest

from crm.core.errors import ConflictError, DomainError, InvalidTransition, NotAllowed
from crm.work import services as work
from crm.work.models import Assignment, AssignmentEvent, Handover, Task

pytestmark = pytest.mark.django_db


def op():
    return uuid.uuid4().hex


def test_claim_from_pool_assigns_and_records_history(users, pool, make_contact):
    c = make_contact(destination="pool", pool=pool)
    a = Assignment.objects.get(contact=c)
    result = work.claim(c, actor=users["ben"], expected_version=a.version, operation_id=op())
    assert result.assignment.kind == "person" and result.assignment.user == users["ben"]
    ev = AssignmentEvent.objects.filter(contact=c, event_type="claimed").get()
    assert ev.from_pool == pool and ev.to_user == users["ben"] and ev.actor == users["ben"]


def test_second_claim_conflicts_and_reports_current_handler(users, pool, make_contact):
    c = make_contact(destination="pool", pool=pool)
    v = Assignment.objects.get(contact=c).version
    work.claim(c, actor=users["ben"], expected_version=v, operation_id=op())
    with pytest.raises(ConflictError) as err:
        work.claim(c, actor=users["ana"], expected_version=v, operation_id=op())
    assert "Ben Broker" in err.value.message
    assert Assignment.objects.get(contact=c).user == users["ben"]


def test_claim_replay_with_same_operation_is_one_transition(users, pool, make_contact):
    c = make_contact(destination="pool", pool=pool)
    v = Assignment.objects.get(contact=c).version
    key = op()
    first = work.claim(c, actor=users["ben"], expected_version=v, operation_id=key)
    again = work.claim(c, actor=users["ben"], expected_version=v, operation_id=key)
    assert again.replayed and not first.replayed
    assert AssignmentEvent.objects.filter(contact=c, event_type="claimed").count() == 1


def test_claim_does_not_touch_source_or_introducer(users, pool, make_contact):
    c = make_contact(destination="pool", pool=pool, introducer=users["max"], source_detail="Spring roadshow")
    work.claim(c, actor=users["ben"], expected_version=1, operation_id=op())
    c.refresh_from_db()
    assert c.introducer == users["max"] and c.source_detail == "Spring roadshow"


def test_transfer_keeps_sender_responsible_until_accepted(users, make_contact):
    c = make_contact()
    h = work.request_handover(c, actor=users["ana"], kind="transfer", recipient=users["ben"], reason="Going on leave",
                              expected_version=1)
    assert Assignment.objects.get(contact=c).user == users["ana"]
    work.accept_handover(h, actor=users["ben"])
    a = Assignment.objects.get(contact=c)
    assert a.user == users["ben"] and a.version == 2
    assert Handover.objects.get(pk=h.pk).state == "accepted"


def test_only_named_recipient_can_accept(users, make_contact):
    c = make_contact()
    h = work.request_handover(c, actor=users["ana"], kind="transfer", recipient=users["ben"], reason="r", expected_version=1)
    with pytest.raises(NotAllowed):
        work.accept_handover(h, actor=users["max"])
    with pytest.raises(NotAllowed):
        work.accept_handover(h, actor=users["ana"])
    assert Assignment.objects.get(contact=c).user == users["ana"]
    assert Handover.objects.get(pk=h.pk).state == "requested"


def test_decline_and_cancel_leave_sender_responsible(users, make_contact):
    c = make_contact()
    h = work.request_handover(c, actor=users["ana"], kind="transfer", recipient=users["ben"], reason="r", expected_version=1)
    work.decline_handover(h, actor=users["ben"], note="Too busy")
    assert Assignment.objects.get(contact=c).user == users["ana"]
    h2 = work.request_handover(c, actor=users["ana"], kind="transfer", recipient=users["max"], reason="r", expected_version=1)
    with pytest.raises(NotAllowed):
        work.cancel_handover(h2, actor=users["max"])
    work.cancel_handover(h2, actor=users["ana"])
    assert Assignment.objects.get(contact=c).user == users["ana"]
    assert Handover.objects.filter(contact=c).count() == 2  # history retained


def test_repeated_acceptance_is_one_logical_transfer(users, make_contact):
    c = make_contact()
    h = work.request_handover(c, actor=users["ana"], kind="transfer", recipient=users["ben"], reason="r", expected_version=1)
    work.accept_handover(h, actor=users["ben"])
    work.accept_handover(h, actor=users["ben"])
    assert AssignmentEvent.objects.filter(contact=c, event_type="handover_accepted").count() == 1
    assert Assignment.objects.get(contact=c).version == 2


def test_only_one_open_handover_per_contact(users, make_contact):
    c = make_contact()
    work.request_handover(c, actor=users["ana"], kind="transfer", recipient=users["ben"], reason="r", expected_version=1)
    with pytest.raises(ConflictError):
        work.request_handover(c, actor=users["ana"], kind="transfer", recipient=users["max"], reason="r", expected_version=1)


def test_non_handler_cannot_request_handover(users, make_contact):
    c = make_contact()
    with pytest.raises(NotAllowed):
        work.request_handover(c, actor=users["ben"], kind="transfer", recipient=users["max"], reason="r", expected_version=1)


def test_stale_request_cannot_overwrite_newer_assignment(users, pool, make_contact):
    c = make_contact(destination="pool", pool=pool)
    # Coordinator offers the pool client to Ana, but Ben claims it first.
    h = work.request_handover(c, actor=users["cora"], kind="transfer", recipient=users["ana"], reason="Fits Ana",
                              expected_version=1)
    work.claim(c, actor=users["ben"], expected_version=1, operation_id=op())
    with pytest.raises((ConflictError, InvalidTransition)):
        work.accept_handover(h, actor=users["ana"])
    assert Assignment.objects.get(contact=c).user == users["ben"]
    assert Handover.objects.get(pk=h.pk).state == "stale"


def test_release_requires_coordinator_acceptance(users, pool, make_contact):
    c = make_contact()
    h = work.request_handover(c, actor=users["ana"], kind="release", pool=pool, reason="Not my area", expected_version=1)
    a = Assignment.objects.get(contact=c)
    assert a.kind == "person" and a.user == users["ana"]  # not claimable while pending
    with pytest.raises(ConflictError):
        work.claim(c, actor=users["ben"], expected_version=a.version, operation_id=op())
    with pytest.raises(NotAllowed):
        work.accept_handover(h, actor=users["ben"])
    work.accept_handover(h, actor=users["cora"])
    a.refresh_from_db()
    assert a.kind == "pool" and a.pool == pool
    work.claim(c, actor=users["ben"], expected_version=a.version, operation_id=op())
    assert Assignment.objects.get(contact=c).user == users["ben"]


def test_release_to_pool_without_coordinator_is_refused(users, make_contact):
    from crm.work.models import Pool

    orphan = Pool.objects.create(name="Orphan pool")
    c = make_contact()
    with pytest.raises(DomainError) as err:
        work.request_handover(c, actor=users["ana"], kind="release", pool=orphan, reason="r", expected_version=1)
    assert err.value.code == "pool_accountability_gap"


def test_open_tasks_need_explicit_disposition_and_follow_it(users, make_contact, frozen):
    c = make_contact()
    keep = work.create_task(c, actor=users["ana"], assignee=users["max"], title="Send brochure", kind="follow_up", due_at=frozen)
    move = work.create_task(c, actor=users["ana"], assignee=users["ana"], title="Call back", kind="call", due_at=frozen)
    with pytest.raises(DomainError) as err:
        work.request_handover(c, actor=users["ana"], kind="transfer", recipient=users["ben"], reason="r", expected_version=1)
    assert err.value.code == "task_disposition_required"
    h = work.request_handover(c, actor=users["ana"], kind="transfer", recipient=users["ben"], reason="r",
                              task_dispositions={keep.pk: "keep", move.pk: "transfer"}, expected_version=1)
    assert Task.objects.get(pk=move.pk).assignee == users["ana"]  # unchanged until acceptance
    work.accept_handover(h, actor=users["ben"])
    assert Task.objects.get(pk=keep.pk).assignee == users["max"]
    assert Task.objects.get(pk=move.pk).assignee == users["ben"]


def test_colleague_completing_task_keeps_ownership(users, make_contact, frozen):
    c = make_contact()
    t = work.create_task(c, actor=users["ana"], assignee=users["ben"], title="Prepare docs", kind="admin", due_at=frozen)
    work.complete_task(t, actor=users["ben"], expected_version=t.version)
    assert Assignment.objects.get(contact=c).user == users["ana"]


def test_task_cannot_be_completed_twice(users, make_contact, frozen):
    c = make_contact()
    t = work.create_task(c, actor=users["ana"], assignee=users["ana"], title="x", kind="call", due_at=frozen)
    work.complete_task(t, actor=users["ana"], expected_version=t.version)
    with pytest.raises(InvalidTransition):
        work.complete_task(t, actor=users["ana"], expected_version=t.version)


def test_replan_keeps_original_due_date(users, make_contact, frozen):
    import datetime as dt

    c = make_contact()
    t = work.create_task(c, actor=users["ana"], assignee=users["ana"], title="x", kind="call", due_at=frozen)
    t2 = work.replan_task(t, actor=users["ana"], due_at=frozen + dt.timedelta(days=2), reason="Customer travelling",
                          expected_version=t.version)
    assert t2.original_due_at == frozen and t2.replan_count == 1
