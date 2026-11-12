"""Customer message transports.

Only the local sandbox transport is implemented. It writes each message as an
.eml file under var/sandbox_mail/ and reports ``sandbox_captured``. It never
contacts a provider, so its results are never presented as real deliveries.

Deterministic failure simulation for tests and demos: addresses at the
reserved domains ``fail.invalid`` (provider error) and ``timeout.invalid``
(timeout = uncertain outcome) fail in the sandbox.
"""
from __future__ import annotations

import os
from email.message import EmailMessage
from pathlib import Path

from django.conf import settings


class TransportError(Exception):
    """Provider rejected or failed the send; safe to retry."""


class TransportTimeout(Exception):
    """Outcome unknown. Must NOT be blindly retried (could duplicate)."""


class SandboxTransport:
    name = "sandbox"
    final_status = "sandbox_captured"

    def __init__(self, directory: Path | None = None):
        self.directory = directory or (settings.VAR_DIR / "sandbox_mail")

    def send(self, *, message_id: int, to: str, subject: str, body: str) -> str:
        domain = to.rsplit("@", 1)[-1].lower() if "@" in to else ""
        if domain == "fail.invalid":
            raise TransportError("Sandbox simulated provider rejection (fail.invalid)")
        if domain == "timeout.invalid":
            raise TransportTimeout("Sandbox simulated timeout (timeout.invalid)")
        self.directory.mkdir(parents=True, exist_ok=True)
        msg = EmailMessage()
        msg["To"] = to
        msg["From"] = "crm-sandbox@localhost.invalid"
        msg["Subject"] = subject
        msg["X-CRM-Message-Id"] = str(message_id)
        msg["X-CRM-Transport"] = "sandbox (not sent)"
        msg.set_content(body)
        path = self.directory / f"message-{message_id}.eml"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(bytes(msg))
        return f"sandbox:{path.name}"


def get_transport():
    name = settings.CRM_EMAIL_TRANSPORT
    if name != "sandbox":
        raise RuntimeError(f"Email transport '{name}' is not implemented; only 'sandbox' is available.")
    return SandboxTransport()
