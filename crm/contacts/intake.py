"""Authorised website/form intake (REQ-003..006).

A narrow, token-authenticated endpoint that records an inquiry. It grants no CRM
read access. It is disabled unless CRM_INTAKE_TOKEN is set. Replays with the
same ``external_id`` return the original result (idempotent). Success is only
reported after the inquiry is committed.

Identity rule (implementation default, configurable later): an exact match on
normalised email to exactly one active contact reuses that identity as a repeat
inquiry. Otherwise a new contact is created in the intake pool; other possible
duplicates (phone/name) are flagged for human review, never merged.
"""
from __future__ import annotations

import hmac
import json
import logging
import os

from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from crm.core.db import write_transaction
from crm.core.errors import DomainError
from crm.core.services import audit
from crm.work.models import Pool

from . import services
from .models import Contact, Inquiry, Source, normalize_email

log = logging.getLogger("crm.intake")
MAX_BODY = 16 * 1024
CHANNELS = {"email", "phone", "sms", "in_person", "other"}


class IntakeError(Exception):
    def __init__(self, status: int, message: str, fields: dict | None = None):
        super().__init__(message)
        self.status, self.message, self.fields = status, message, fields or {}


def _token() -> str:
    return os.environ.get("CRM_INTAKE_TOKEN", "") or getattr(settings, "CRM_INTAKE_TOKEN", "")


def intake_pool() -> Pool:
    name = os.environ.get("CRM_INTAKE_POOL", "") or getattr(settings, "CRM_INTAKE_POOL", "")
    pools = Pool.objects.filter(active=True)
    if name:
        pool = pools.filter(name=name).first()
        if pool is None:
            raise IntakeError(503, "The configured intake pool does not exist or is inactive.")
        return pool
    if pools.count() != 1:
        raise IntakeError(503, "Set CRM_INTAKE_POOL: intake needs exactly one destination pool.")
    return pools.get()


def validate(payload) -> dict:
    if not isinstance(payload, dict):
        raise IntakeError(400, "Expected a JSON object.")
    errors = {}
    clean = {}
    for key, limit in (("external_id", 120), ("name", 150), ("email", 254), ("phone", 40), ("message", 4000),
                       ("source", 50), ("channel", 20), ("source_detail", 200)):
        value = payload.get(key, "")
        if value is None:
            value = ""
        if not isinstance(value, str):
            errors[key] = "Must be a string."
            continue
        value = value.strip()
        if len(value) > limit:
            errors[key] = f"At most {limit} characters."
        clean[key] = value
    if not clean.get("external_id"):
        errors["external_id"] = "Required (your form submission id); it makes retries safe."
    if not clean.get("message"):
        errors["message"] = "Required."
    if not clean.get("name") and not clean.get("email") and not clean.get("phone"):
        errors["name"] = "Give at least a name, email or phone."
    if clean.get("email"):
        try:
            validate_email(clean["email"])
        except ValidationError:
            errors["email"] = "Not a valid email address."
    if clean.get("channel") and clean["channel"] not in CHANNELS:
        errors["channel"] = f"One of {sorted(CHANNELS)}."
    if clean.get("source") and not Source.objects.filter(code=clean["source"], active=True).exists():
        errors["source"] = "Unknown source code."
    if errors:
        raise IntakeError(400, "Invalid intake payload.", errors)
    return clean


def record(data: dict) -> tuple[Inquiry, bool, int]:
    """Persist the inquiry. Returns (inquiry, created, duplicate_candidates)."""
    key = f"intake:{data['external_id']}"
    existing = Inquiry.objects.filter(external_key=key).select_related("contact").first()
    if existing:
        return existing, False, 0
    pool = intake_pool()
    source = Source.objects.filter(code=data["source"]).first() if data.get("source") else None
    channel = data.get("channel") or "email"

    def run():
        again = Inquiry.objects.filter(external_key=key).first()
        if again:
            return again, False, 0
        email = normalize_email(data.get("email", ""))
        matches = list(Contact.objects.filter(email_normalized=email, archived_at__isnull=True)) if email else []
        if len(matches) == 1:
            inquiry = services.record_inquiry(matches[0], actor=None, message=data["message"], channel=channel,
                                              source=source, external_key=key)
            return inquiry, True, 0
        result = services.capture_contact(
            actor=None, destination="pool", pool=pool,
            data={"display_name": data.get("name") or data.get("email") or data.get("phone"), "email": data.get("email", ""),
                  "phone": data.get("phone", ""), "source": source, "source_detail": data.get("source_detail", "")},
        )
        inquiry = services.record_inquiry(result.contact, actor=None, message=data["message"], channel=channel, source=source,
                                          external_key=key)
        candidates = services.duplicate_candidates(email=data.get("email", ""), phone=data.get("phone", ""),
                                                   name=data.get("name", ""), exclude_id=result.contact.pk).count()
        if candidates:
            audit("intake.possible_duplicate", result.contact, f"Web intake created a new contact; {candidates} possible "
                  "duplicate(s) need review (not merged)", actor=None, actor_kind="system", contact=result.contact)
        return inquiry, True, candidates

    return write_transaction(run)


@csrf_exempt
@login_not_required
@require_POST
def intake_view(request):
    expected = _token()
    if not expected:
        return JsonResponse({"error": "Intake is disabled."}, status=404)
    supplied = request.headers.get("Authorization", "")
    if not supplied.startswith("Bearer ") or not hmac.compare_digest(supplied[7:].encode(), expected.encode()):
        log.warning("intake rejected: bad token", extra={"remote": request.META.get("REMOTE_ADDR", "")})
        return JsonResponse({"error": "Unauthorized."}, status=401)
    declared = request.headers.get("Content-Length")
    # HTTP allows digits only. Python's int() also accepts underscores and a leading sign.
    if declared is not None and (not declared.isascii() or not declared.isdecimal()):
        return JsonResponse({"error": "Content-Length is not a number."}, status=400)
    declared_length = int(declared) if declared else 0
    if declared_length < 0 or declared_length > MAX_BODY or len(request.body) > MAX_BODY:
        return JsonResponse({"error": "Payload too large."}, status=413)
    try:
        payload = json.loads(request.body.decode("utf-8") or "null")
        data = validate(payload)
        inquiry, created, candidates = record(data)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Body must be UTF-8 JSON."}, status=400)
    except IntakeError as exc:
        return JsonResponse({"error": exc.message, "fields": exc.fields}, status=exc.status)
    except DomainError as exc:
        return JsonResponse({"error": exc.message}, status=getattr(exc, "status", 400))
    body = {"status": "created" if created else "replayed", "inquiry_id": inquiry.pk, "contact_id": inquiry.contact_id,
            "possible_duplicates": candidates}
    return JsonResponse(body, status=201 if created else 200)
