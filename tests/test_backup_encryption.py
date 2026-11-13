"""Encrypted backups (product step 4): no plain copy on disk, wrong key and tampering refused, restore works."""
import json
import sqlite3

import pytest

from crm.contacts.models import Contact
from crm.core import backup, backup_crypto


@pytest.fixture
def key(settings):
    settings.CRM_BACKUP_KEY = backup_crypto.new_key()
    return settings.CRM_BACKUP_KEY


@pytest.mark.django_db(transaction=True)
def test_encrypted_backup_round_trip(key, tmp_path, settings, users, make_contact):
    settings.CRM_BACKUP_DIR = tmp_path / "bk"
    make_contact("Before Backup")
    path = backup.create_backup()
    assert path.name.endswith(".sqlite3.enc")
    assert [p.name for p in path.parent.iterdir() if p.suffix == ".sqlite3"] == []  # plain copy removed
    assert b"Before Backup" not in path.read_bytes()
    with pytest.raises(sqlite3.DatabaseError):
        sqlite3.connect(str(path)).execute("select 1 from sqlite_master").fetchall()
    manifest = backup.verify_backup(path)
    assert manifest["encrypted"] and manifest["key_id"] == backup_crypto.key_id(backup_crypto.parse_key(key))
    make_contact("After Backup")
    safety = backup.restore_backup(path, confirm=path.name)
    assert list(Contact.objects.values_list("display_name", flat=True)) == ["Before Backup"]
    assert safety.name.endswith(".enc")
    assert [p.name for p in path.parent.iterdir() if p.name.startswith(".verify-")] == []


@pytest.mark.django_db(transaction=True)
def test_wrong_or_missing_key_is_refused(key, tmp_path, settings, users):
    path = backup.create_backup(tmp_path / "bk")
    settings.CRM_BACKUP_KEY = backup_crypto.new_key()
    with pytest.raises(backup.BackupError, match="not the key"):
        backup.verify_backup(path)
    settings.CRM_BACKUP_KEY = ""
    with pytest.raises(backup.BackupError, match="encrypted"):
        backup.verify_backup(path)


def test_tampered_or_truncated_ciphertext_fails(tmp_path):
    k = backup_crypto.parse_key(backup_crypto.new_key())
    src = tmp_path / "plain.bin"
    src.write_bytes(b"x" * (backup_crypto.CHUNK * 2 + 10))
    enc = tmp_path / "plain.bin.enc"
    backup_crypto.encrypt_file(src, enc, k)
    out = tmp_path / "out.bin"
    backup_crypto.decrypt_file(enc, out, k)
    assert out.read_bytes() == src.read_bytes()
    data = bytearray(enc.read_bytes())
    data[100] ^= 1
    bad = tmp_path / "bad.enc"
    bad.write_bytes(bytes(data))
    with pytest.raises(backup_crypto.BackupKeyError):
        backup_crypto.decrypt_file(bad, out, k)
    cut = tmp_path / "cut.enc"
    cut.write_bytes(enc.read_bytes()[:-(4 + 10 + 16)])  # drop the whole last chunk record
    with pytest.raises(backup_crypto.BackupKeyError, match="truncated"):
        backup_crypto.decrypt_file(cut, out, k)


@pytest.mark.django_db(transaction=True)
def test_prune_keeps_newest_and_safety_copies(tmp_path, settings, users):
    settings.CRM_BACKUP_DIR = tmp_path / "bk"
    made = [backup.create_backup() for _ in range(4)]
    safety = backup.create_backup(label="pre-restore")
    removed = backup.prune_backups(keep=2)
    assert sorted(removed) == sorted(made[:2])
    left = backup.list_backups()
    assert safety in left and made[3] in left and made[2] in left
    assert all(json.loads(backup.manifest_path(p).read_text())["file"] == p.name for p in left)


def test_deploy_check_warns_without_backup_key(settings):
    from crm.core.checks import backup_and_mail_settings

    settings.CRM_BACKUP_KEY = ""
    assert "crm.W001" in [w.id for w in backup_and_mail_settings(None)]
    settings.CRM_BACKUP_KEY = backup_crypto.new_key()
    assert "crm.W001" not in [w.id for w in backup_and_mail_settings(None)]


@pytest.mark.django_db(transaction=True)
def test_bad_key_leaves_no_plain_backup(tmp_path, settings, users):
    settings.CRM_BACKUP_KEY = "not-a-valid-key"
    with pytest.raises(backup.BackupError):
        backup.create_backup(tmp_path / "bk")
    assert not (tmp_path / "bk").exists() or list((tmp_path / "bk").iterdir()) == []
