"""Structured, redacted logging."""
from __future__ import annotations

import json
import logging
import re

SENSITIVE_KEYS = re.compile(r"(pass(word)?|secret|token|session|cookie|csrf|authorization|api[_-]?key)", re.I)
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+)")


def redact_value(key: str, value):
    if SENSITIVE_KEYS.search(key or ""):
        return "[redacted]"
    if isinstance(value, str):
        return EMAIL_RE.sub(r"\1***@\2", value)
    if isinstance(value, dict):
        return {k: redact_value(k, v) for k, v in value.items()}
    return value


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = EMAIL_RE.sub(r"\1***@\2", record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(EMAIL_RE.sub(r"\1***@\2", a) if isinstance(a, str) else a for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {k: redact_value(k, v) for k, v in record.args.items()}
        for key, value in list(record.__dict__.items()):
            if key in _STANDARD:
                continue
            record.__dict__[key] = redact_value(key, value)
        return True


_STANDARD = set(logging.LogRecord("x", 0, "x", 0, "x", None, None).__dict__) | {"message", "asctime"}


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD and not key.startswith("_"):
                try:
                    json.dumps(value)
                    payload[key] = value
                except TypeError:
                    payload[key] = repr(value)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info).splitlines()[-1]
        return json.dumps(payload)
