"""Operational commands: backup/restore, admin bootstrap, demo seed, migrations."""
import os
import stat

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from crm.accounts.models import User
from crm.contacts.models import Contact
from crm.core import backup


@pytest.mark.django_db(transaction=True)
def test_backup_is_consistent_private_and_restorable(settings, tmp_path, users, make_contact):
    make_contact("Before Backup")
    path = backup.create_backup(tmp_path / "bk")
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    manifest = backup.verify_backup(path)
    assert manifest["integrity_check"] == "ok" and manifest["encrypted"] is False

    make_contact("After Backup")
    assert Contact.objects.count() == 2

    with pytest.raises(backup.BackupError):
        backup.restore_backup(path, confirm="")  # never implicit
    safety = backup.restore_backup(path, confirm=path.name)
    assert safety is not None and safety.exists()
    assert list(Contact.objects.values_list("display_name", flat=True)) == ["Before Backup"]

    # The safety copy holds the state from just before the restore.
    backup.restore_backup(safety, confirm=safety.name)
    assert Contact.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_tampered_backup_is_refused(tmp_path, users):
    path = backup.create_backup(tmp_path / "bk")
    with path.open("r+b") as fh:
        fh.seek(200)
        fh.write(b"corrupted!")
    with pytest.raises(backup.BackupError, match="checksum"):
        backup.verify_backup(path)
    with pytest.raises(backup.BackupError):
        backup.restore_backup(path, confirm=path.name)
    path.with_suffix(".json").unlink()
    with pytest.raises(backup.BackupError, match="manifest"):
        backup.verify_backup(path)


@pytest.mark.django_db
def test_create_admin_has_no_default_password(capsys, monkeypatch):
    monkeypatch.delenv("CRM_ADMIN_PASSWORD", raising=False)
    call_command("create_admin", "--email", "Boss@Example.test", "--generate")
    out = capsys.readouterr().out
    password = out.strip().splitlines()[-1].split(": ", 1)[1]
    user = User.objects.get(email="boss@example.test")
    assert user.is_staff and user.must_change_password and user.check_password(password)
    with pytest.raises(CommandError):
        call_command("create_admin", "--email", "boss@example.test", "--generate")
    monkeypatch.setenv("CRM_ADMIN_PASSWORD", "short")
    with pytest.raises(CommandError):
        call_command("create_admin", "--email", "other@example.test")


@pytest.mark.django_db
def test_seed_demo_builds_story_and_refuses_twice(monkeypatch, frozen):
    monkeypatch.setenv("CRM_DEMO_PASSWORD", "demo-password-for-tests-1")
    call_command("seed_demo")
    assert User.objects.filter(email__endswith="@demo.example.test").count() == 5
    assert User.objects.get(email="ana@demo.example.test").check_password("demo-password-for-tests-1")
    from crm.attention import services as attention
    from crm.core.services import get_policy

    summary = attention.summarize(attention.evaluate(now=frozen, policy=get_policy()))
    for reason in ("inquiry_awaiting", "toured_no_followup", "task_overdue", "pool_waiting", "handover_waiting", "inactive"):
        assert summary["per_reason"][reason] >= 1, reason
    from crm.automation.models import Job
    from crm.comms.models import OutboundMessage

    statuses = set(OutboundMessage.objects.values_list("status", flat=True))
    assert {"uncertain", "sandbox_captured"} <= statuses  # frozen at 10:00 local: outside quiet hours
    rejected = OutboundMessage.objects.get(to_address="paolo@fail.invalid")
    assert rejected.status in ("scheduled", "failed")  # retried with backoff, never shown as delivered
    assert Job.objects.filter(kind="comms.send", last_error__contains="fail.invalid").exists()
    with pytest.raises(CommandError):
        call_command("seed_demo")


@pytest.mark.django_db
def test_seed_demo_refuses_in_production(settings):
    settings.CRM_ENV = "production"
    with pytest.raises(CommandError):
        call_command("seed_demo")


@pytest.mark.django_db
def test_no_missing_migrations():
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)


def test_logs_redact_secrets_and_emails():
    import logging

    from crm.core.logging import RedactingFilter, StructuredFormatter

    record = logging.LogRecord("crm", logging.INFO, __file__, 1, "login for %s", ("carla@example.test",), None)
    record.password = "hunter2-hunter2"
    record.session_key = "abc123"
    record.detail = {"to": "noah@example.test", "api_key": "k-123"}
    assert RedactingFilter().filter(record)
    line = StructuredFormatter().format(record)
    for secret in ("hunter2", "abc123", "k-123", "carla@example.test", "noah@example.test"):
        assert secret not in line
    assert "c***@example.test" in line


def test_fresh_database_migrates_from_zero(tmp_path):
    """Migrations apply cleanly to an empty file and leave nothing unapplied (no shared test DB involved)."""
    import subprocess
    import sys

    env = {**os.environ, "CRM_ENV": "development", "CRM_VAR_DIR": str(tmp_path), "CRM_DB_PATH": str(tmp_path / "fresh.sqlite3")}
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run([sys.executable, "manage.py", "migrate", "-v0"], cwd=root, env=env, check=True)
    subprocess.run([sys.executable, "manage.py", "migrate", "--check", "-v0"], cwd=root, env=env, check=True)
    subprocess.run([sys.executable, "manage.py", "check", "--fail-level", "WARNING"], cwd=root, env=env, check=True,
                   capture_output=True)
    import sqlite3

    conn = sqlite3.connect(tmp_path / "fresh.sqlite3")
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("SELECT count(*) FROM automation_rule").fetchone()[0] >= 10  # reference data migration
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
