"""Online SQLite backup and verified restore.

Backups use SQLite's online backup API, so they are consistent while the app and
worker keep running (WAL mode). Each backup is integrity-checked, written with
0600 permissions and described by a JSON manifest holding its SHA-256.

When CRM_BACKUP_KEY is set, backups are encrypted (AES-256-GCM, see backup_crypto) and the
plain copy never stays on disk. Without a key they are plain SQLite files: protect the
directory and treat backup files as containing personal data.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sqlite3
from pathlib import Path

from django.conf import settings
from django.db import connections

from . import backup_crypto


class BackupError(Exception):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def integrity_check(path: Path) -> str:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return conn.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        conn.close()


def _db_path() -> Path:
    if "sqlite3" not in settings.DATABASES["default"]["ENGINE"]:
        raise BackupError("backup_db/restore_db only support SQLite. Use your database's own backup tooling.")
    return Path(settings.DATABASES["default"]["NAME"])


def _latest_migrations(path: Path) -> dict[str, str]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT app, max(name) FROM django_migrations GROUP BY app").fetchall()
    finally:
        conn.close()
    return dict(rows)


def _key() -> bytes | None:
    value = getattr(settings, "CRM_BACKUP_KEY", "")
    if not value:
        return None
    try:
        return backup_crypto.parse_key(value)
    except backup_crypto.BackupKeyError as exc:
        raise BackupError(str(exc)) from exc


def manifest_path(path: Path) -> Path:
    name = path.name.removesuffix(".enc").removesuffix(".sqlite3")
    return path.with_name(name + ".json")


def list_backups(directory: Path | None = None) -> list[Path]:
    directory = Path(directory or settings.CRM_BACKUP_DIR)
    if not directory.is_dir():
        return []
    files = [p for p in directory.iterdir() if p.name.startswith("crm-") and p.name.endswith((".sqlite3", ".sqlite3.enc"))]
    return sorted(files, key=lambda p: p.name, reverse=True)


def prune_backups(directory: Path | None = None, *, keep: int) -> list[Path]:
    """Delete all but the newest ``keep`` regular backups (pre-restore safety copies are never pruned)."""
    regular = [p for p in list_backups(directory) if "-pre-restore" not in p.name]
    removed = []
    for old in regular[keep:]:
        manifest_path(old).unlink(missing_ok=True)
        old.unlink(missing_ok=True)
        removed.append(old)
    return removed


def create_backup(directory: Path | None = None, *, label: str = "") -> Path:
    key = _key()  # validate before any plain copy exists
    directory = Path(directory or settings.CRM_BACKUP_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S%fZ")
    target = directory / f"crm-{stamp}{('-' + label) if label else ''}.sqlite3"
    source = sqlite3.connect(str(_db_path()))
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    dest = sqlite3.connect(str(target))
    try:
        source.backup(dest)
        # A self-contained file: no -wal/-shm side files that could hold (unencrypted) pages.
        dest.execute("PRAGMA journal_mode=DELETE")
    finally:
        dest.close()
        source.close()
    os.chmod(target, 0o600)
    result = integrity_check(target)
    if result != "ok":
        _remove_plain(target)
        raise BackupError(f"Backup failed its integrity check: {result}")
    manifest = {
        "created_utc": stamp,
        "plain_sha256": _sha256(target),
        "plain_bytes": target.stat().st_size,
        "integrity_check": result,
        "migrations": _latest_migrations(target),
        "encrypted": False,
    }
    if key is not None:
        encrypted = target.with_name(target.name + ".enc")
        try:
            backup_crypto.encrypt_file(target, encrypted, key)
        finally:
            _remove_plain(target)
        target = encrypted
        manifest.update({"encrypted": True, "cipher": "AES-256-GCM chunked v1", "key_id": backup_crypto.key_id(key)})
    manifest.update({"file": target.name, "sha256": _sha256(target), "bytes": target.stat().st_size})
    mpath = manifest_path(target)
    mpath.write_text(json.dumps(manifest, indent=2))
    os.chmod(mpath, 0o600)
    return target


def _remove_plain(plain: Path) -> None:
    for suffix in ("", "-wal", "-shm", "-journal"):
        plain.with_name(plain.name + suffix).unlink(missing_ok=True)


def _plain_copy(path: Path, manifest: dict) -> tuple[Path, bool]:
    """Return a readable SQLite file for ``path`` and whether it is a temporary decrypted copy."""
    if not manifest.get("encrypted"):
        return path, False
    key = _key()
    if key is None:
        raise BackupError("This backup is encrypted. Set CRM_BACKUP_KEY to the key it was made with.")
    if manifest.get("key_id") and manifest["key_id"] != backup_crypto.key_id(key):
        raise BackupError("CRM_BACKUP_KEY is not the key this backup was made with.")
    plain = path.with_name(f".verify-{os.getpid()}-{path.name.removesuffix('.enc')}")
    try:
        backup_crypto.decrypt_file(path, plain, key)
    except backup_crypto.BackupKeyError as exc:
        _remove_plain(plain)
        raise BackupError(str(exc)) from exc
    return plain, True


def verify_backup(path: Path, *, keep_plain: bool = False) -> dict:
    path = Path(path)
    if not path.is_file():
        raise BackupError(f"No backup at {path}")
    mpath = manifest_path(path)
    if not mpath.is_file():
        raise BackupError("Backup manifest is missing; refusing to trust this file.")
    manifest = json.loads(mpath.read_text())
    if _sha256(path) != manifest["sha256"]:
        raise BackupError("Backup checksum does not match its manifest (file changed or corrupted).")
    plain, temporary = _plain_copy(path, manifest)
    try:
        if "plain_sha256" in manifest and _sha256(plain) != manifest["plain_sha256"]:
            raise BackupError("Decrypted backup does not match its manifest.")
        result = integrity_check(plain)
        if result != "ok":
            raise BackupError(f"Backup failed its integrity check: {result}")
    except BaseException:
        if temporary:
            _remove_plain(plain)
        raise
    if temporary and not keep_plain:
        _remove_plain(plain)
    elif temporary:
        manifest["_plain_path"] = str(plain)
    return manifest


def restore_backup(path: Path, *, confirm: str) -> Path:
    """Replace the live database with a verified backup. A safety backup of the current DB is taken first.

    ``confirm`` must equal the backup file name: restoring is never implicit.
    """
    path = Path(path)
    if confirm != path.name:
        raise BackupError("Restore not confirmed. Pass --confirm with the exact backup file name.")
    manifest = verify_backup(path, keep_plain=True)
    plain = Path(manifest.get("_plain_path") or path)
    try:
        current = _db_path()
        safety = create_backup(label="pre-restore") if current.exists() else None
        connections.close_all()
        src = sqlite3.connect(f"file:{plain}?mode=ro", uri=True)
        dst = sqlite3.connect(str(current))
        try:
            src.backup(dst)
            dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            dst.close()
            src.close()
    finally:
        if plain != path:
            _remove_plain(plain)
    result = integrity_check(current)
    if result != "ok":
        raise BackupError(f"Restored database failed its integrity check: {result}. Safety copy: {safety}")
    return safety
