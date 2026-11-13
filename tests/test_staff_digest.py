"""Staff digest email is a second copy of the in-app digest, never a customer send."""
import datetime as dt

import pytest

from crm.automation import engine
from crm.automation.models import DigestSnapshot, Job, Notification
from crm.comms.models import OutboundMessage
from crm.core import clock
from crm.core.models import AuditEvent
from crm.core.services import get_policy, get_settings_row, update_policy

pytestmark = pytest.mark.django_db
DAY = dt.datetime(2026, 11, 16, 3, tzinfo=dt.UTC)


def _file_mail(settings, tmp_path):
    mail_dir = tmp_path / "staff_mail"
    settings.EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
    settings.EMAIL_FILE_PATH = mail_dir
    return mail_dir


def _ana_snapshot():
    return DigestSnapshot.objects.get(recipient__email="ana@example.test")


def test_staff_copy_is_filed_once_and_is_not_a_customer_message(settings, tmp_path, users, make_contact):
    mail_dir = _file_mail(settings, tmp_path)
    with clock.frozen(DAY):
        make_contact("Digest Dora")
        engine.run_digest()
    job = Job.objects.get(kind="staff.digest_email")
    assert engine.deliver_staff_digest(job) == {"status": "filed"}
    assert engine.deliver_staff_digest(job) == {"status": "filed"}
    files = list(mail_dir.iterdir())
    assert len(files) == 1
    text = files[0].read_text()
    assert "not sent to a customer" in text
    assert "for staff only" in text
    assert "need attention" in text
    snap = _ana_snapshot()
    assert snap.email_state == "filed"
    assert "not a customer message" in snap.email_note.lower()
    assert AuditEvent.objects.filter(action="staff.digest_emailed", object_id=str(snap.pk)).count() == 1
    assert not OutboundMessage.objects.exists()
    with clock.frozen(DAY):
        engine.run_digest()
    assert Job.objects.filter(kind="staff.digest_email").count() == 1
    assert Notification.objects.filter(kind="digest", recipient=users["ana"]).count() == 1


def test_staff_copy_is_skipped_when_the_setting_is_off(settings, tmp_path, users, make_contact):
    mail_dir = _file_mail(settings, tmp_path)
    row = get_settings_row()
    policy = get_policy()
    policy["notifications"]["digest_email"] = False
    update_policy(policy, actor=users["admin"], expected_version=row.version, note="digest email off")
    with clock.frozen(DAY):
        make_contact("Quiet Quinn")
        engine.run_digest()
    assert not Job.objects.filter(kind="staff.digest_email").exists()
    assert _ana_snapshot().email_state == "skipped"
    assert Notification.objects.filter(kind="digest", recipient=users["ana"]).exists()
    assert list(mail_dir.glob("*")) == []
    assert not OutboundMessage.objects.exists()


def test_turning_the_setting_off_skips_a_queued_copy(settings, tmp_path, users, make_contact):
    mail_dir = _file_mail(settings, tmp_path)
    with clock.frozen(DAY):
        make_contact("Queued Quinn")
        engine.run_digest()
    row = get_settings_row()
    policy = get_policy()
    policy["notifications"]["digest_email"] = False
    update_policy(policy, actor=users["admin"], expected_version=row.version, note="stop staff copy")
    job = Job.objects.get(kind="staff.digest_email")
    assert engine.deliver_staff_digest(job) == {"status": "skipped"}
    assert _ana_snapshot().email_state == "skipped"
    assert list(mail_dir.glob("*")) == []


def test_deactivated_recipient_is_not_emailed(settings, tmp_path, users, make_contact):
    mail_dir = _file_mail(settings, tmp_path)
    with clock.frozen(DAY):
        make_contact("Left Lane")
        engine.run_digest()
    users["ana"].is_active = False
    users["ana"].save(update_fields=["is_active"])
    job = Job.objects.get(kind="staff.digest_email", payload__snapshot_id=_ana_snapshot().pk)
    assert engine.deliver_staff_digest(job) == {"status": "skipped"}
    assert "No active staff email address." in _ana_snapshot().email_note
    assert list(mail_dir.glob("*")) == []


def test_failed_prepare_stays_queued_and_can_be_retried(monkeypatch, settings, tmp_path, users, make_contact):
    mail_dir = _file_mail(settings, tmp_path)
    with clock.frozen(DAY):
        make_contact("Retry Rae")
        engine.run_digest()
    job = Job.objects.get(kind="staff.digest_email")

    def boom(*args, **kwargs):
        raise OSError("mail folder unavailable")

    monkeypatch.setattr("django.core.mail.send_mail", boom)
    with pytest.raises(OSError):
        engine.deliver_staff_digest(job)
    assert _ana_snapshot().email_state == "queued"
    monkeypatch.undo()
    assert engine.deliver_staff_digest(job) == {"status": "filed"}
    assert len(list(mail_dir.iterdir())) == 1


def test_smtp_backend_is_labelled_handed_to_staff_mail(monkeypatch, settings, users, make_contact):
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    sent = {}

    def capture(subject, body, from_email, recipients, fail_silently=False):
        sent["subject"] = subject
        sent["body"] = body
        sent["recipients"] = recipients
        return 1

    monkeypatch.setattr("django.core.mail.send_mail", capture)
    with clock.frozen(DAY):
        make_contact("Smtp Sam")
        engine.run_digest()
    job = Job.objects.get(kind="staff.digest_email", payload__snapshot_id=_ana_snapshot().pk)
    assert engine.deliver_staff_digest(job) == {"status": "smtp"}
    snap = _ana_snapshot()
    assert snap.email_state == "smtp"
    assert "not a customer message" in snap.email_note.lower()
    assert "delivered" not in snap.email_note.lower()
    assert sent["recipients"] == [users["ana"].email]
    assert "not sent to a customer" in sent["body"]
    assert not OutboundMessage.objects.exists()


def test_notification_page_shows_the_staff_copy_state(client, settings, tmp_path, users, make_contact):
    _file_mail(settings, tmp_path)
    with clock.frozen(DAY):
        make_contact("Visible Vera")
        engine.run_digest()
    engine.deliver_staff_digest(Job.objects.get(kind="staff.digest_email", payload__snapshot_id=_ana_snapshot().pk))
    client.post("/accounts/login/", {"email": users["ana"].email, "password": "a-long-test-password-1"})
    body = client.get("/automation/notifications/").content.decode()
    assert "Staff copy filed (not a customer message)" in body
