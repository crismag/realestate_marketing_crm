"""View helpers shared by the CRM screens."""
from __future__ import annotations

import uuid

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import redirect

from .errors import DomainError


def run_action(request, fn, *, success: str, redirect_to: str):
    """Run a service call from a POST and report the domain outcome as a visible message."""
    try:
        result = fn()
    except DomainError as exc:
        messages.error(request, exc.message)
        return redirect(redirect_to), None
    if success:
        messages.success(request, success)
    return redirect(redirect_to), result


def paginate(request, queryset, per_page: int = 25):
    paginator = Paginator(queryset, per_page)
    page = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return page, params.urlencode()


def new_operation_id() -> str:
    return uuid.uuid4().hex


def safe_next(request, default: str) -> str:
    from django.utils.http import url_has_allowed_host_and_scheme

    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        return target
    return default
