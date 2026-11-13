"""Duplicate merge: moves history, archives the duplicate, never takes a client from someone (product step 3)."""
import pytest

from crm.contacts import merging, services
from crm.contacts.models import Contact, Interaction, Watch
from crm.core.errors import DomainError
from crm.work import services as work
from crm.work.models import Task

pytestmark = pytest.mark.django_db


def test_merge_moves_records_and_archives_duplicate(users, make_contact, frozen):
    keep = make_contact("Maria Santos", email="maria@example.test", notes="VIP")
    dup = make_contact("Maria Santos", phone="+63 917 555 0199", notes="Met at roadshow", inquiry="Condo please")
    services.record_interaction(dup, actor=users["ana"], kind="conversation", channel="phone", summary="Called",
                                occurred_at=frozen)
    work.create_task(dup, actor=users["ana"], assignee=users["ana"], title="Send listings", kind="follow_up",
                     due_at=frozen)
    services.watch(dup, actor=users["ben"])
    keep.refresh_from_db()
    dup.refresh_from_db()
    merged = merging.merge_contacts(keep, dup, actor=users["ana"], keep_version=keep.version,
                                    duplicate_version=dup.version)
    assert merged.phone == "+63 917 555 0199" and merged.phone_normalized  # empty field filled and indexed
    assert "VIP" in merged.notes and "Met at roadshow" in merged.notes
    assert Interaction.objects.filter(contact=merged).count() == 1
    assert Task.objects.filter(contact=merged, title="Send listings").exists()
    assert Watch.objects.filter(contact=merged, user=users["ben"]).exists()
    assert merged.inquiries.count() == 1
    dup = Contact.objects.get(pk=dup.pk)
    assert dup.archived_at is not None and dup.merged_into_id == merged.pk


def test_cannot_merge_contacts_held_by_different_people(users, make_contact):
    keep = make_contact("Maria Santos", actor=users["ana"])
    dup = make_contact("Maria Santos", actor=users["ben"])
    plan = merging.plan_merge(keep, dup)
    assert plan.blockers and "Hand one over" in plan.blockers[0]
    with pytest.raises(DomainError):
        merging.merge_contacts(keep, dup, actor=users["ana"], keep_version=keep.version, duplicate_version=dup.version)


def test_only_the_responsible_person_can_merge(users, make_contact):
    keep = make_contact("Maria Santos", actor=users["ana"])
    dup = make_contact("Maria Santos", actor=users["ana"])
    with pytest.raises(DomainError):
        merging.merge_contacts(keep, dup, actor=users["ben"], keep_version=keep.version, duplicate_version=dup.version)


def test_opt_out_and_lifecycle_carry_over(users, make_contact):
    keep = make_contact("Maria Santos")
    dup = make_contact("Maria Santos")
    services.set_email_opt_out(dup, actor=users["ana"], opted_out=True)
    dup.refresh_from_db()
    services.set_lifecycle(dup, actor=users["ana"], lifecycle="client", disposition="active", reason="",
                           expected_version=dup.version)
    dup.refresh_from_db()
    merged = merging.merge_contacts(keep, dup, actor=users["ana"], keep_version=keep.version, duplicate_version=dup.version)
    assert merged.email_opt_out and merged.lifecycle == "client"


def test_merge_screens(client, users, make_contact):
    keep = make_contact("Maria Santos", email="maria@example.test")
    dup = make_contact("Maria Santos", email="maria+work@example.test")
    client.force_login(users["ana"])
    page = client.get(f"/contacts/{keep.pk}/").content.decode()
    assert "Possible duplicates" in page and f"/contacts/{keep.pk}/merge/{dup.pk}/" in page
    assert client.get(f"/contacts/{keep.pk}/merge/{dup.pk}/").status_code == 200
    r = client.post(f"/contacts/{keep.pk}/merge/{dup.pk}/", {"keep_version": keep.version, "duplicate_version": dup.version})
    assert r.status_code == 302
    assert "merged into" in client.get(f"/contacts/{dup.pk}/").content.decode()
