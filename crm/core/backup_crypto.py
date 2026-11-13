"""Authenticated encryption for backup files (AES-256-GCM in 1 MiB chunks).

File layout: MAGIC | 8-byte random prefix | repeated [4-byte big-endian length | ciphertext+tag].
Each chunk's nonce is prefix + chunk counter, and its associated data binds the counter and a "last chunk"
flag, so chunks cannot be reordered, dropped or the file truncated without decryption failing.
The key is 32 random bytes, given as URL-safe base64 in CRM_BACKUP_KEY. Keep a copy of the key somewhere
other than the server: without it the backups cannot be read by anyone, including you.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import struct
from pathlib import Path

MAGIC = b"CRMBACKUP1\n"
CHUNK = 1 << 20


class BackupKeyError(Exception):
    pass


def new_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def parse_key(value: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value.strip().encode())
    except (ValueError, TypeError) as exc:
        raise BackupKeyError("CRM_BACKUP_KEY is not valid base64.") from exc
    if len(key) != 32:
        raise BackupKeyError("CRM_BACKUP_KEY must decode to 32 bytes. Generate one with `manage.py backup_key`.")
    return key


def key_id(key: bytes) -> str:
    return hashlib.sha256(b"crm-backup-key-id" + key).hexdigest()[:12]


def _aad(counter: int, last: bool) -> bytes:
    return MAGIC + struct.pack(">I?", counter, last)


def encrypt_file(src: Path, dst: Path, key: bytes) -> None:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    aes = AESGCM(key)
    prefix = secrets.token_bytes(8)
    fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out, src.open("rb") as fh:
        out.write(MAGIC + prefix)
        counter = 0
        chunk = fh.read(CHUNK)
        while True:
            nxt = fh.read(CHUNK)
            last = not nxt
            ct = aes.encrypt(prefix + struct.pack(">I", counter), chunk, _aad(counter, last))
            out.write(struct.pack(">I", len(ct)) + ct)
            if last:
                break
            chunk, counter = nxt, counter + 1


def decrypt_file(src: Path, dst: Path, key: bytes) -> None:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    aes = AESGCM(key)
    fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as out, src.open("rb") as fh:
        if fh.read(len(MAGIC)) != MAGIC:
            raise BackupKeyError("Not an encrypted CRM backup.")
        prefix = fh.read(8)
        counter, finished = 0, False
        while True:
            head = fh.read(4)
            if not head:
                break
            if finished:
                raise BackupKeyError("Backup has data after its last chunk.")
            (length,) = struct.unpack(">I", head)
            ct = fh.read(length)
            nonce = prefix + struct.pack(">I", counter)
            try:
                try:
                    plain = aes.decrypt(nonce, ct, _aad(counter, False))
                except InvalidTag:
                    plain = aes.decrypt(nonce, ct, _aad(counter, True))
                    finished = True
            except InvalidTag as exc:
                raise BackupKeyError("Backup cannot be decrypted: wrong key, or the file was changed.") from exc
            out.write(plain)
            counter += 1
        if not finished:
            raise BackupKeyError("Backup is truncated (last chunk missing).")
