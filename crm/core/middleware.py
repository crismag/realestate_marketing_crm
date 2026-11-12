from __future__ import annotations

import threading
import uuid
import zoneinfo

from django.utils import timezone

_local = threading.local()


def current_request_id() -> str:
    return getattr(_local, "request_id", "")


class RequestContextMiddleware:
    """Assign a request id used in audit records and logs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request_id = str(uuid.uuid4())
        request.request_id = _local.request_id
        try:
            response = self.get_response(request)
        finally:
            _local.request_id = ""
        response["X-Request-ID"] = request.request_id
        return response


class WorkspaceTimezoneMiddleware:
    """Display times in the workspace timezone; storage stays UTC."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(request, "user", None) is not None and request.user.is_authenticated:
            from .services import get_policy

            policy = get_policy()
            request.crm_policy = policy
            try:
                timezone.activate(zoneinfo.ZoneInfo(policy["timezone"]))
            except (zoneinfo.ZoneInfoNotFoundError, ValueError):
                timezone.deactivate()
        try:
            return self.get_response(request)
        finally:
            timezone.deactivate()


CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", CSP)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if getattr(request, "user", None) is not None and request.user.is_authenticated:
            response.setdefault("Cache-Control", "no-store")
        return response
