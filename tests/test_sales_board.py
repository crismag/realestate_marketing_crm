"""Sales board: stage moves stay on the opportunity and do not touch responsibility or lifecycle."""
import datetime as dt
from pathlib import Path

import pytest

from crm.contacts import services
from crm.core.models import AuditEvent
from crm.core.services import get_policy, get_settings_row, update_policy
from crm.core.settings_forms import PolicyForm
from crm.work.models import AssignmentEvent

PASSWORD = "a-long-test-password-1"


def login(client, user):
    client.post("/accounts/login/", {"email": user.email, "password": PASSWORD})


def _open(contact, actor, title, stage="new", amount=2500000):
    return services.save_opportunity(
        contact, actor=actor, opportunity=None, expected_version=None,
        data={"title": title, "stage": stage, "amount_minor": amount, "currency": "USD"},
    )


@pytest.mark.django_db
def test_board_groups_stages_and_ships_real_overlay_controls(client, users, make_contact, frozen):
    contact = make_contact("Board Bea")
    _open(contact, users["ana"], "Park 2-bedroom", stage="new")
    _open(contact, users["ana"], "Old file", stage="legacy")
    login(client, users["ana"])
    body = client.get("/contacts/opportunities/?view=board").content.decode()
    assert 'data-cg="tabs"' in body and 'data-cg="drawer"' in body and 'data-cg="modal"' in body
    assert "crm/behaviors.js" in body
    assert 'data-stage="new"' in body and "Park 2-bedroom" in body
    assert 'data-stage="other"' in body and "Old file" in body
    assert 'aria-label="Move stage for Park 2-bedroom"' in body
    assert 'aria-label="Move stage for Old file"' in body
    list_body = client.get("/contacts/opportunities/?view=list").content.decode()
    assert "Park 2-bedroom" in list_body and 'id="sales-panel-list"' in list_body


@pytest.mark.django_db
def test_stage_move_keeps_handler_lifecycle_and_amount(client, users, make_contact, frozen):
    from crm.core import clock

    contact = make_contact("Board Bea")
    opp = _open(contact, users["ana"], "Park 2-bedroom")
    assignment_version = contact.assignment.version
    events = AssignmentEvent.objects.filter(contact=contact).count()
    clock.set_frozen(frozen + dt.timedelta(days=3))
    login(client, users["ben"])
    resp = client.post(f"/contacts/opportunities/{opp.pk}/stage/", {
        "stage": "viewing", "version": opp.version, "view": "board", "outcome": "open", "filter_stage": "",
    }, follow=True)
    body = resp.content.decode()
    assert "Stage updated." in body
    opp.refresh_from_db()
    contact.refresh_from_db()
    assert opp.stage == "viewing" and opp.version == 2
    assert opp.amount_minor == 2500000 and opp.outcome == "open"
    assert opp.stage_changed_at == frozen + dt.timedelta(days=3)
    assert contact.lifecycle == "lead"
    assert contact.assignment.user_id == users["ana"].pk
    assert contact.assignment.version == assignment_version
    assert AssignmentEvent.objects.filter(contact=contact).count() == events
    assert AuditEvent.objects.filter(action="opportunity.stage_changed", object_id=str(opp.pk)).exists()
    assert resp.redirect_chain[-1][0].startswith("/contacts/opportunities/?")
    assert "view=board" in resp.redirect_chain[-1][0]


@pytest.mark.django_db
def test_same_stage_is_a_noop(client, users, make_contact, frozen):
    contact = make_contact("Board Bea")
    opp = _open(contact, users["ana"], "Park 2-bedroom")
    login(client, users["ana"])
    resp = client.post(f"/contacts/opportunities/{opp.pk}/stage/", {"stage": "new", "version": opp.version}, follow=True)
    opp.refresh_from_db()
    assert opp.version == 1 and opp.stage == "new"
    assert "already in this stage" in resp.content.decode()
    assert not AuditEvent.objects.filter(action="opportunity.stage_changed", object_id=str(opp.pk)).exists()


@pytest.mark.django_db
def test_closed_unknown_and_stale_stage_moves_are_refused(client, users, make_contact, frozen, policy):
    contact = make_contact("Board Bea")
    opp = _open(contact, users["ana"], "Park 2-bedroom", stage="decision")
    services.close_opportunity(
        opp, actor=users["ana"], outcome="lost", reason="Budget", expected_version=opp.version, policy=policy,
    )
    opp.refresh_from_db()
    login(client, users["ana"])
    closed = client.post(f"/contacts/opportunities/{opp.pk}/stage/", {"stage": "new", "version": opp.version}, follow=True)
    opp.refresh_from_db()
    assert opp.outcome == "lost" and opp.stage == "decision"
    assert "until reopened" in closed.content.decode()
    contact.refresh_from_db()
    assert contact.lifecycle == "lead"

    other = _open(contact, users["ana"], "Second deal", stage="new")
    unknown = client.post(
        f"/contacts/opportunities/{other.pk}/stage/", {"stage": "nope", "version": other.version}, follow=True,
    )
    other.refresh_from_db()
    assert other.stage == "new" and "Unknown stage." in unknown.content.decode()

    services.move_opportunity_stage(
        other, actor=users["ana"], stage="qualification", expected_version=other.version, policy=get_policy(),
    )
    stale = client.post(
        f"/contacts/opportunities/{other.pk}/stage/", {"stage": "viewing", "version": other.version}, follow=True,
    )
    other.refresh_from_db()
    assert other.stage == "qualification"
    assert "changed by someone else" in stale.content.decode()


@pytest.mark.django_db
def test_board_limit_is_configurable_and_reported(client, users, make_contact, frozen):
    contact = make_contact("Board Bea")
    _open(contact, users["ana"], "First")
    _open(contact, users["ana"], "Second")
    row = get_settings_row()
    policy = get_policy()
    policy["sales_board_limit"] = 1
    update_policy(policy, actor=users["admin"], expected_version=row.version, note="test board limit")
    login(client, users["ana"])
    body = client.get("/contacts/opportunities/?view=board&outcome=open").content.decode()
    assert "Showing 1 of 2 matches" in body


@pytest.mark.django_db
def test_settings_form_saves_board_limit(users):
    policy = get_policy()
    initial = PolicyForm.initial_from(policy, get_settings_row().version)
    data = {}
    for key, value in initial.items():
        if key == "escalation_recipients":
            data[key] = [user.pk for user in value]
        elif key == "contact_reset_types":
            data[key] = list(value)
        elif isinstance(value, bool):
            if value:
                data[key] = "on"
        else:
            data[key] = value
    data["sales_board_limit"] = "40"
    data["note"] = "board size"
    form = PolicyForm(data)
    assert form.is_valid(), form.errors
    assert form.to_policy(policy)["sales_board_limit"] == 40


def test_behavior_script_does_not_set_inline_styles():
    text = (Path(__file__).resolve().parent.parent / "static/crm/behaviors.js").read_text()
    assert ".style" not in text
    assert "setAttribute(\"style\"" not in text
    assert "drawer.open" in text and "modal.open" in text
