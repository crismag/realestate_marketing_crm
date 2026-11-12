"""Online SQLite backup and verified restore.

Backups use SQLite's online backup API, so they are consistent while the app and
worker keep running (WAL mode). Each backup is integrity-checked, written with
0600 permissions and described by a JSON manifest holding its SHA-256.

Backups are NOT encrypted. Protect the backup directory (disk encryption,
restricted permissions) and treat backup files as containing personal data.
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


def create_backup(directory: Path | None = None, *, label: str = "") -> Path:
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
    finally:
        dest.close()
        source.close()
    os.chmod(target, 0o600)
    result = integrity_check(target)
    if result != "ok":
        target.unlink(missing_ok=True)
        raise BackupError(f"Backup failed its integrity check: {result}")
    manifest = {
        "file": target.name,
        "created_utc": stamp,
        "sha256": _sha256(target),
        "bytes": target.stat().st_size,
        "integrity_check": result,
        "migrations": _latest_migrations(target),
        "encrypted": False,
    }
    manifest_path = target.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, indent=2))
    os.chmod(manifest_path, 0o600)
    return target


def verify_backup(path: Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise BackupError(f"No backup at {path}")
    manifest_path = path.with_suffix(".json")
    if not manifest_path.is_file():
        raise BackupError("Backup manifest is missing; refusing to trust this file.")
    manifest = json.loads(manifest_path.read_text())
    if _sha256(path) != manifest["sha256"]:
        raise BackupError("Backup checksum does not match its manifest (file changed or corrupted).")
    result = integrity_check(path)
    if result != "ok":
        raise BackupError(f"Backup failed its integrity check: {result}")
    return manifest


def restore_backup(path: Path, *, confirm: str) -> Path:
    """Replace the live database with a verified backup. A safety backup of the current DB is taken first.

    ``confirm`` must equal the backup file name: restoring is never implicit.
    """
    path = Path(path)
    if confirm != path.name:
        raise BackupError("Restore not confirmed. Pass --confirm with the exact backup file name.")
    verify_backup(path)
    current = _db_path()
    safety = create_backup(label="pre-restore") if current.exists() else None
    connections.close_all()
    src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    dst = sqlite3.connect(str(current))
    try:
        src.backup(dst)
        dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        dst.close()
        src.close()
    result = integrity_check(current)
    if result != "ok":
        raise BackupError(f"Restored database failed its integrity check: {result}. Safety copy: {safety}")
    return safety
