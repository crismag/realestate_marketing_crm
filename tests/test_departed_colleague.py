"""A deactivated colleague's clients must not get stuck (pilot finding, 2026-11-13)."""
import pytest

from crm.attention import services as attention
from crm.core.errors import NotAllowed
from crm.work import services as work
from crm.work.models import Assignment

pytestmark = pytest.mark.django_db


def _deactivate(user):
    user.is_active = False
    user.save(update_fields=["is_active"])


def test_admin_can_start_handover_for_deactivated_colleague_and_ownership_waits_for_acceptance(users, make_contact):
    c = make_contact(actor=users["ana"])
    _deactivate(users["ana"])
    a = Assignment.objects.get(contact=c)
    h = work.request_handover(c, actor=users["admin"], kind="transfer", recipient=users["ben"],
                              reason="Ana left the company", expected_version=a.version)
    # ADR-001: nothing changes hands until the recipient accepts.
    assert Assignment.objects.get(contact=c).user == users["ana"]
    work.accept_handover(h, actor=users["ben"])
    assert Assignment.objects.get(contact=c).user == users["ben"]


def test_non_admin_cannot_move_a_deactivated_colleagues_client(users, make_contact):
    c = make_contact(actor=users["ana"])
    _deactivate(users["ana"])
    a = Assignment.objects.get(contact=c)
    with pytest.raises(NotAllowed):
        work.request_handover(c, actor=users["ben"], kind="transfer", recipient=users["max"],
                              reason="x", expected_version=a.version)


def test_admin_cannot_move_an_active_colleagues_client(users, make_contact):
    c = make_contact(actor=users["ana"])
    a = Assignment.objects.get(contact=c)
    with pytest.raises(NotAllowed):
        work.request_handover(c, actor=users["admin"], kind="transfer", recipient=users["ben"],
                              reason="x", expected_version=a.version)


def test_deactivated_handler_shows_in_attention_for_admins(users, make_contact, policy):
    c = make_contact(actor=users["ana"])
    _deactivate(users["ana"])
    items = attention.evaluate(policy=policy, contact_ids=[c.pk])
    reason = next(r for r in items[0].reasons if r.code == "handler_inactive")
    assert users["admin"] in reason.recipients
    mine = attention.filter_items(items, user=users["admin"], scope="mine")
    assert [i.contact.pk for i in mine] == [c.pk]


def test_deactivating_user_warns_about_held_clients(client, users, make_contact):
    make_contact(actor=users["ana"])
    client.force_login(users["admin"])
    r = client.post(f"/accounts/users/{users['ana'].pk}/", {"full_name": "Ana Agent", "title": "", "is_active": "",
                                                              "is_staff": ""}, follow=True)
    assert r.status_code == 200
    assert "still holds 1 client" in r.content.decode()


def test_multi_checkbox_lists_are_checkboxes_not_radios(db):
    from crm.core.settings_forms import PolicyForm

    form = PolicyForm()
    assert form.fields["contact_reset_types"].widget.attrs["class"] == "cg-checkbox"


def test_source_code_is_derived_from_label(client, users):
    from crm.contacts.models import Source

    client.force_login(users["admin"])
    client.post("/settings/sources/new/", {"label": "Open house — Makati", "code": "", "kind": "other", "active": "on"})
    assert Source.objects.filter(code="open-house-makati").exists()
