"""Two-step sign-in with an authenticator app (RFC 6238 TOTP, SHA-1, 6 digits, 30 s).

Works with Google Authenticator, Microsoft Authenticator, 1Password, Authy and similar apps.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import secrets
import struct
from urllib.parse import quote, urlencode

STEP_SECONDS = 30
DIGITS = 6
WINDOW = 1  # accept one step either side for clock drift


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _key(secret: str) -> bytes:
    padded = secret + "=" * (-len(secret) % 8)
    return base64.b32decode(padded.upper())


def code_at(secret: str, step: int) -> str:
    digest = hmac.new(_key(secret), struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**DIGITS).zfill(DIGITS)


def matching_step(secret: str, code: str, *, timestamp: float, after_step: int = 0) -> int | None:
    """Return the time step the code belongs to, or None. Steps at or before ``after_step`` are refused (no replay)."""
    code = "".join(ch for ch in (code or "") if ch.isdigit())
    if len(code) != DIGITS or not secret:
        return None
    current = int(timestamp // STEP_SECONDS)
    for step in range(current - WINDOW, current + WINDOW + 1):
        if step > after_step and hmac.compare_digest(code_at(secret, step), code):
            return step
    return None


def provisioning_uri(secret: str, *, account: str, issuer: str) -> str:
    label = quote(f"{issuer}:{account}")
    return f"otpauth://totp/{label}?" + urlencode({"secret": secret, "issuer": issuer, "digits": DIGITS,
                                                   "period": STEP_SECONDS})


def qr_svg(uri: str) -> str:
    import segno

    out = io.BytesIO()
    segno.make(uri, error="m").save(out, kind="svg", xmldecl=False, svgns=True, scale=5, border=2,
                                     svgclass="totp-qr", lineclass=None)
    return out.getvalue().decode()


def new_recovery_codes(n: int = 8) -> list[str]:
    return [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(n)]


def hash_code(code: str) -> str:
    return hashlib.sha256(code.strip().lower().encode()).hexdigest()
