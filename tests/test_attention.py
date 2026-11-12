"""AT-003 / AT-005: forgotten-client attention, reasons, freshness and counting."""
import datetime as dt

import pytest

from crm.attention import services as attention
from crm.contacts import services as contacts
from crm.core import clock
from crm.work import services as work

pytestmark = pytest.mark.django_db
H = dt.timedelta(hours=1)
D = dt.timedelta(days=1)


def reasons_for(contact, policy, now):
    items = attention.evaluate(now=now, policy=policy, contact_ids=[contact.pk])
    return {r.code for r in items[0].active_reasons} if items else set()


def test_toured_client_without_task_appears_after_window(users, make_contact, policy, now):
    with clock.frozen(now - 5 * D):
        c = make_contact("Tia Toured")
        contacts.record_interaction(c, actor=users["ana"], kind="meeting_tour", channel="in_person",
                                    summary="Viewed unit 4B", occurred_at=now - 5 * D)
    assert "toured_no_followup" in reasons_for(c, policy, now)
    assert "toured_no_followup" not in reasons_for(c, policy, now - 5 * D + 47 * H)
    with clock.frozen(now):
        contacts.record_interaction(c, actor=users["ana"], kind="outbound_attempt", channel="phone",
                                    summary="Left voicemail", occurred_at=now - H)
    assert "toured_no_followup" not in reasons_for(c, policy, now)


def test_profile_view_and_notes_do_not_count_as_contact(client, users, make_contact, policy, now):
    with clock.frozen(now - 30 * D):
        c = make_contact("Quiet Quinn")
    client.force_login(users["ana"])
    with clock.frozen(now):
        client.get(f"/contacts/{c.pk}/")
        contacts.record_interaction(c, actor=users["ana"], kind="note", channel="other", summary="Internal note",
                                    occurred_at=now - H)
    assert "inactive" in reasons_for(c, policy, now)


def test_inactivity_is_explained_and_missing_history_not_invented(users, make_contact, policy, now):
    with clock.frozen(now - 10 * D):
        c = make_contact("Never Called")
    items = attention.evaluate(now=now, policy=policy, contact_ids=[c.pk])
    inactive = [r for r in items[0].reasons if r.code == "inactive"][0]
    assert "No contact recorded since capture" in inactive.detail
    assert items[0].last_success is None and items[0].last_attempt is None


def test_future_task_does_not_hide_unanswered_inquiry(users, make_contact, policy, now):
    with clock.frozen(now - 2 * H):
        c = make_contact("Ivy Inquiry", inquiry="Is the condo still available?")
        work.create_task(c, actor=users["ana"], assignee=users["ana"], title="Call", kind="call", due_at=now + D)
    codes = reasons_for(c, policy, now)
    assert "inquiry_awaiting" in codes and "next_action_missing" not in codes


def test_overdue_task_keeps_ownership_and_assignment_does_not_clear_it(users, make_contact, policy, now):
    with clock.frozen(now - 3 * D):
        c = make_contact("Olga Overdue")
        work.create_task(c, actor=users["ana"], assignee=users["ana"], title="Send offer", kind="follow_up", due_at=now - D)
    items = attention.evaluate(now=now, policy=policy, contact_ids=[c.pk])
    assert "task_overdue" in {r.code for r in items[0].reasons}
    assert items[0].handler_users == [users["ana"]]


def test_one_client_three_reasons_counts_once(users, make_contact, policy, now):
    with clock.frozen(now - 20 * D):
        c = make_contact("Multi Reason", inquiry="Hello?")
        contacts.record_interaction(c, actor=users["ana"], kind="meeting_tour", channel="in_person", summary="Tour",
                                    occurred_at=now - 20 * D)
        work.create_task(c, actor=users["ana"], assignee=users["ana"], title="x", kind="call", due_at=now - 2 * D)
    items = attention.evaluate(now=now, policy=policy)
    summary = attention.summarize(items)
    assert summary["unique_contacts"] == 1
    assert sum(summary["per_reason"].values()) >= 3


def test_agreed_later_contact_suppresses_cadence_but_not_inquiry(users, make_contact, policy, now):
    with clock.frozen(now - 30 * D):
        c = make_contact("Later Larry", inquiry="Call me next month", next_contact_agreed_at=now + 10 * D)
    codes = reasons_for(c, policy, now)
    assert "inactive" not in codes and "next_action_missing" not in codes
    assert "inquiry_awaiting" in codes


def test_snooze_hides_then_resurfaces_without_rewriting_history(users, make_contact, policy, now):
    with clock.frozen(now - 30 * D):
        c = make_contact("Snoozy Sam")
    with clock.frozen(now):
        attention.snooze(c, actor=users["ana"], reason_code="inactive", until=now + 2 * D, note="On holiday")
    assert "inactive" not in reasons_for(c, policy, now)
    assert "inactive" in reasons_for(c, policy, now + 3 * D)


def test_overdue_task_cannot_be_snoozed(users, make_contact, now):
    from crm.core.errors import DomainError

    c = make_contact()
    with clock.frozen(now), pytest.raises(DomainError):
        attention.snooze(c, actor=users["ana"], reason_code="task_overdue", until=now + D, note="x")


def test_pending_handover_routes_reminder_to_sender_and_recipient(users, make_contact, policy, now):
    with clock.frozen(now - 2 * D):
        c = make_contact("Hand Over")
        work.request_handover(c, actor=users["ana"], kind="transfer", recipient=users["ben"], reason="Leave", expected_version=1)
    item = attention.evaluate(now=now, policy=policy, contact_ids=[c.pk])[0]
    hw = [r for r in item.reasons if r.code == "handover_waiting"][0]
    assert hw.overdue and users["ana"] in hw.recipients and users["ben"] in hw.recipients
    assert item.handler_users == [users["ana"]]


def test_coverage_zero_denominator_is_not_applicable(users, policy, now):
    result = attention.coverage(now=now, policy=policy, user=users["max"])
    assert result["eligible"] == 0 and result["ratio"] is None


def test_coverage_counts_met_and_missing_history(users, make_contact, policy, now):
    with clock.frozen(now - 20 * D):
        a = make_contact("Called Recently")
        make_contact("Never Contacted")
    with clock.frozen(now):
        contacts.record_interaction(a, actor=users["ana"], kind="conversation", channel="phone", summary="Chat",
                                    occurred_at=now - D)
    result = attention.coverage(now=now, policy=policy, user=users["ana"])
    assert result["eligible"] == 2 and result["met"] == 1 and result["missing_history"] == 1
    assert result["ratio"] == 0.5
