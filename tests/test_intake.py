"""Website/form intake API: authorised, validated, idempotent, no CRM read access."""
import json

import pytest

from crm.contacts.models import Contact, Inquiry

TOKEN = "test-intake-token-0123456789abcdef"
URL = "/api/intake/inquiries"


def post(client, payload, token=TOKEN, raw=None):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    return client.post(URL, data=raw if raw is not None else json.dumps(payload), content_type="application/json", **headers)


@pytest.fixture
def enabled(monkeypatch, pool):
    monkeypatch.setenv("CRM_INTAKE_TOKEN", TOKEN)
    monkeypatch.delenv("CRM_INTAKE_POOL", raising=False)
    return pool


GOOD = {"external_id": "form-1", "name": "Web Wendy", "email": "wendy@example.test", "message": "Is unit 5 free?",
        "source": "website"}


@pytest.mark.django_db
def test_disabled_without_token(client, monkeypatch, pool):
    monkeypatch.delenv("CRM_INTAKE_TOKEN", raising=False)
    assert post(client, GOOD).status_code == 404
    assert not Contact.objects.exists()


@pytest.mark.django_db
def test_rejects_missing_or_wrong_token(client, enabled):
    assert post(client, GOOD, token=None).status_code == 401
    assert post(client, GOOD, token="wrong").status_code == 401
    assert not Contact.objects.exists()


@pytest.mark.django_db
def test_creates_pool_contact_and_replay_is_idempotent(client, enabled, users):
    first = post(client, GOOD)
    assert first.status_code == 201
    body = first.json()
    contact = Contact.objects.get(pk=body["contact_id"])
    assert contact.assignment.pool == enabled and contact.source.code == "website"
    again = post(client, GOOD)
    assert again.status_code == 200 and again.json()["status"] == "replayed"
    assert again.json()["inquiry_id"] == body["inquiry_id"]
    assert Contact.objects.count() == 1 and Inquiry.objects.count() == 1


@pytest.mark.django_db
def test_known_email_reuses_identity(client, enabled, make_contact):
    existing = make_contact("Wendy W", email="WENDY@example.test")
    resp = post(client, {**GOOD, "external_id": "form-2"})
    assert resp.status_code == 201 and resp.json()["contact_id"] == existing.pk
    assert Contact.objects.count() == 1 and existing.inquiries.count() == 1
    existing.refresh_from_db()
    assert existing.assignment.user is not None  # responsibility unchanged by intake


@pytest.mark.django_db
def test_phone_or_name_match_is_flagged_not_merged(client, enabled, make_contact):
    make_contact("Web Wendy", phone="+63 917 555 0111")
    resp = post(client, {**GOOD, "external_id": "form-3", "email": "other@example.test", "phone": "0063 917 555 0111"})
    assert resp.status_code == 201 and resp.json()["possible_duplicates"] == 1
    assert Contact.objects.count() == 2


@pytest.mark.django_db
def test_invalid_payload_is_explained_and_nothing_saved(client, enabled):
    resp = post(client, {"external_id": "", "email": "nope", "message": "", "source": "made-up"})
    assert resp.status_code == 400
    fields = resp.json()["fields"]
    assert {"external_id", "email", "message", "source"} <= set(fields)
    assert post(client, None, raw="{not json").status_code == 400
    assert post(client, None, raw=json.dumps({**GOOD, "message": "x" * 20000})).status_code == 413
    assert not Contact.objects.exists()


@pytest.mark.django_db
def test_intake_token_grants_no_read_access(client, enabled):
    resp = client.get("/contacts/", HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
    assert resp.status_code == 302 and resp["Location"].startswith("/accounts/login/")
    assert client.get(URL, HTTP_AUTHORIZATION=f"Bearer {TOKEN}").status_code == 405


@pytest.mark.django_db
def test_ambiguous_pool_configuration_fails_visibly(client, enabled, users):
    from crm.work.models import Pool

    Pool.objects.create(name="Second pool", coordinator=users["cora"])
    resp = post(client, GOOD)
    assert resp.status_code == 503 and "CRM_INTAKE_POOL" in resp.json()["error"]
    assert not Contact.objects.exists()
