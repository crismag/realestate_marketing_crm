"""Daily changes compare durable delivered snapshots, not activity timestamps."""
import datetime as dt

import pytest

from crm.automation import engine
from crm.automation.models import Job, Notification
from crm.contacts.models import Contact
from crm.core import clock

pytestmark = pytest.mark.django_db
DAY = dt.datetime(2026, 11, 16, 3, tzinfo=dt.UTC)


def digest_for(user):
    return Notification.objects.filter(kind="digest", recipient=user).latest("created_at", "id")


def test_first_digest_counts_old_and_undated_attention_as_new(users, make_contact):
    with clock.frozen(DAY - dt.timedelta(days=60)):
        make_contact("Old source timestamp")
    with clock.frozen(DAY):
        engine.run_digest()
    note = digest_for(users["ana"])
    assert "1 new" in note.title
    assert "0 continuing" in note.title
    assert "0 resolved" in note.title
    assert "previous delivered digest" in note.body


def test_changes_and_resolved_only_digest_survive_daily_replay(users, make_contact):
    with clock.frozen(DAY):
        old = make_contact("Will resolve")
        engine.run_digest()
        Contact.objects.filter(pk=old.pk).update(archived_at=DAY)
        new = make_contact("Will continue")
        engine.run_digest()  # Must not overwrite this day's delivered baseline.
    assert Notification.objects.filter(kind="digest", recipient=users["ana"]).count() == 1
    with clock.frozen(DAY + dt.timedelta(days=1)):
        engine.run_digest()
    note = digest_for(users["ana"])
    assert "1 new" in note.title and "0 continuing" in note.title and "1 resolved" in note.title
    with clock.frozen(DAY + dt.timedelta(days=2)):
        engine.run_digest()
    note = digest_for(users["ana"])
    assert "0 new" in note.title and "1 continuing" in note.title and "0 resolved" in note.title
    Contact.objects.filter(pk=new.pk).update(archived_at=DAY)
    with clock.frozen(DAY + dt.timedelta(days=3)):
        engine.run_digest()
        engine.run_digest()
    note = digest_for(users["ana"])
    assert "0 client(s)" in note.title and "1 resolved" in note.title
    assert Notification.objects.filter(kind="digest", recipient=users["ana"]).count() == 4
    with clock.frozen(DAY + dt.timedelta(days=4)):
        engine.run_digest()
    assert Notification.objects.filter(kind="digest", recipient=users["ana"]).count() == 4


def test_digest_change_baselines_are_per_recipient(users, make_contact):
    with clock.frozen(DAY):
        c = make_contact("Shared visibility")
        engine.run_digest()
    from crm.work.models import Assignment

    Assignment.objects.filter(contact=c).update(user=users["ben"])
    with clock.frozen(DAY + dt.timedelta(days=1)):
        engine.run_digest()
    assert "1 resolved" in digest_for(users["ana"]).title
    assert "1 new" in digest_for(users["ben"]).title


def test_snapshot_and_notification_roll_back_together(monkeypatch, users, make_contact):
    from crm.automation.models import DigestSnapshot

    with clock.frozen(DAY):
        make_contact()
        def fail(*args, **kwargs):
            raise RuntimeError("snapshot write failed")
        monkeypatch.setattr(DigestSnapshot.objects, "create", fail)
        with pytest.raises(RuntimeError, match="snapshot write failed"):
            engine.run_digest()
    assert not Notification.objects.filter(kind="digest").exists()
    assert not Job.objects.filter(kind="staff.digest_email").exists()
