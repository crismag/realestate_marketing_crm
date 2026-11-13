"""Posted numbers that do not fit in SQLite must be a message, never a server error."""
import json

import pytest

from crm.contacts.models import Contact
from crm.work import services as work
from crm.work.models import Assignment, Task

pytestmark = pytest.mark.django_db

HUGE = "9" * 40


def test_non_decimal_version_digits_are_a_message(client, users, pool, make_contact, frozen):
    contact = make_contact("Superscript", email="super@example.test")
    client.force_login(users["ana"])
    edited = client.post(f"/contacts/{contact.pk}/edit/", {"display_name": "Renamed", "version": "²"})
    assert edited.status_code == 200
    assert "The page version was not valid." in edited.content.decode()
    contact.refresh_from_db()
    assert contact.display_name == "Superscript"

    pooled = make_contact("Circled", destination="pool", pool=pool, email="circled@example.test")
    client.force_login(users["ben"])
    claimed = client.post(f"/work/claim/{pooled.pk}/", {"version": "①", "operation_id": "circled-claim"}, follow=True)
    assert claimed.status_code == 200
    assert "Missing assignment version" in claimed.content.decode()
    assert Assignment.objects.get(contact=pooled).kind == "pool"

    task = work.create_task(contact, actor=users["ana"], assignee=users["ana"], title="Call back",
                            kind="call", due_at=frozen)
    client.force_login(users["ana"])
    completed = client.post(f"/work/tasks/{task.pk}/complete/", {"version": "²", "note": "done"}, follow=True)
    assert completed.status_code == 200
    assert "Reload the page and try again." in completed.content.decode()
    assert Task.objects.get(pk=task.pk).status == "open"


def test_contact_edit_rejects_an_oversized_version(client, users, make_contact):
    contact = make_contact("Bound Contact", email="bound@example.test")
    client.force_login(users["ana"])
    resp = client.post(f"/contacts/{contact.pk}/edit/", {"display_name": "Renamed", "version": HUGE})
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "The page version was not valid." in body
    assert f'name="version" value="{contact.version}"' in body
    contact.refresh_from_db()
    assert contact.display_name == "Bound Contact"


def test_claim_rejects_an_oversized_version(client, users, pool, make_contact):
    contact = make_contact("Pool Person", destination="pool", pool=pool, email="pool@example.test")
    client.force_login(users["ben"])
    resp = client.post(f"/work/claim/{contact.pk}/", {"version": HUGE, "operation_id": "bound-claim"}, follow=True)
    assert resp.status_code == 200
    assert "Missing assignment version" in resp.content.decode()
    assert Assignment.objects.get(contact=contact).kind == "pool"


def test_task_complete_rejects_an_oversized_version(client, users, make_contact, frozen):
    contact = make_contact("Task Person", email="task@example.test")
    task = work.create_task(contact, actor=users["ana"], assignee=users["ana"], title="Call back",
                            kind="call", due_at=frozen)
    client.force_login(users["ana"])
    resp = client.post(f"/work/tasks/{task.pk}/complete/", {"version": HUGE, "note": "done"}, follow=True)
    assert resp.status_code == 200
    assert "Reload the page and try again." in resp.content.decode()
    assert Task.objects.get(pk=task.pk).status == "open"


def test_merge_rejects_oversized_versions(client, users, make_contact):
    keep = make_contact("Keep Me", email="keep@example.test")
    duplicate = make_contact("Drop Me", email="drop@example.test")
    client.force_login(users["ana"])
    resp = client.post(
        f"/contacts/{keep.pk}/merge/{duplicate.pk}/",
        {"keep_version": HUGE, "duplicate_version": HUGE, "reason": "same person"},
        follow=True,
    )
    assert resp.status_code == 200
    assert "Reload the page and try again." in resp.content.decode()
    assert Contact.objects.filter(pk=duplicate.pk, archived_at__isnull=True).exists()


def test_attention_filters_ignore_oversized_ids(client, users, make_contact):
    make_contact("Visible", email="visible@example.test")
    client.force_login(users["ana"])
    resp = client.get("/attention/", {"pool": HUGE, "team": HUGE, "person": HUGE})
    assert resp.status_code == 200


def test_snooze_rejects_a_day_count_outside_the_form(client, users, make_contact):
    contact = make_contact("Snooze Me", email="snooze@example.test")
    client.force_login(users["ana"])
    resp = client.post(f"/attention/snooze/{contact.pk}/", {"reason_code": "inactive", "days": HUGE}, follow=True)
    assert resp.status_code == 200
    assert "Choose 1, 3, 7, 14, or 30 days." in resp.content.decode()
    assert contact.snoozes.count() == 0


def test_intake_rejects_a_non_numeric_content_length(client, monkeypatch, pool):
    monkeypatch.setenv("CRM_INTAKE_TOKEN", "test-intake-token-0123456789abcdef")
    resp = client.post(
        "/api/intake/inquiries",
        data=json.dumps({"external_id": "bound-1", "name": "Len", "email": "len@example.test", "message": "Hi"}),
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer test-intake-token-0123456789abcdef",
        CONTENT_LENGTH="abc",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Content-Length is not a number."
    assert not Contact.objects.exists()
