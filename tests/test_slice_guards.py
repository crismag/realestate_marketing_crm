"""Guards for the sales board, staff digest, and priority score that the earlier slices did not cover."""
import pytest
from django.test import Client

from crm.automation.models import Notification
from crm.contacts import services as contacts
from crm.core.services import get_policy, get_settings_row, update_policy

pytestmark = pytest.mark.django_db


def _opportunity(users, make_contact):
    contact = make_contact("Guard Deal", inquiry="Is it free?")
    return contacts.save_opportunity(
        contact, actor=users["ana"], opportunity=None, expected_version=None,
        data={"title": "Guard file", "stage": "new", "amount_minor": 1, "currency": "USD"},
    )


def test_anonymous_posts_to_new_actions_are_sent_to_login(client, users, make_contact):
    opp = _opportunity(users, make_contact)
    stage = client.post(f"/contacts/opportunities/{opp.pk}/stage/", {"stage": "qualification", "version": opp.version})
    assert stage.status_code == 302 and stage["Location"].startswith("/accounts/login/")
    note = Notification.objects.create(
        recipient=users["ana"], kind="digest", title="Ana private digest", reason="Daily", logical_key="guard-anon",
    )
    dismissed = client.post(f"/automation/notifications/{note.pk}/dismiss/")
    assert dismissed.status_code == 302 and dismissed["Location"].startswith("/accounts/login/")
    opp.refresh_from_db()
    assert opp.stage == "new"


def test_stage_move_rejects_a_missing_csrf_token(users, make_contact):
    opp = _opportunity(users, make_contact)
    client = Client(enforce_csrf_checks=True)
    client.force_login(users["ana"])
    resp = client.post(f"/contacts/opportunities/{opp.pk}/stage/", {"stage": "qualification", "version": str(opp.version)})
    assert resp.status_code == 403
    opp.refresh_from_db()
    assert opp.stage == "new"


def test_agent_cannot_change_priority_or_digest_settings(client, users):
    client.force_login(users["ana"])
    resp = client.post("/settings/", {
        "priority_score_enabled": "", "digest_email": "", "note": "nope",
        "version": str(get_settings_row().version),
    })
    assert resp.status_code == 403
    policy = get_policy()
    assert policy["attention"]["priority"]["enabled"] is True
    assert policy["notifications"]["digest_email"] is True


def test_one_person_cannot_see_or_dismiss_anothers_notification(client, users):
    note = Notification.objects.create(
        recipient=users["ana"], kind="digest", title="Ana private digest", reason="Daily", logical_key="guard-private",
    )
    client.force_login(users["ben"])
    assert "Ana private digest" not in client.get("/automation/notifications/").content.decode()
    assert client.post(f"/automation/notifications/{note.pk}/dismiss/").status_code == 404
    note.refresh_from_db()
    assert note.dismissed_at is None


def test_priority_explanation_escapes_a_stage_label(client, users, make_contact, now, frozen):
    policy = get_policy()
    policy["opportunity_stages"][0]["label"] = "<script>alert(1)</script>"
    update_policy(policy, actor=users["admin"], expected_version=get_settings_row().version, note="label")
    _opportunity(users, make_contact)
    client.force_login(users["ana"])
    body = client.get("/").content.decode()
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
