"""Audit and workspace-policy services."""
from __future__ import annotations

import copy

from django.db import transaction

from . import clock
from .errors import ConflictError
from .logging import redact_value
from .middleware import current_request_id
from .models import AuditEvent, SettingsVersion, WorkspaceSettings
from .policy import merged


def audit(action: str, obj, summary: str, *, actor=None, contact=None, data: dict | None = None, actor_kind: str | None = None):
    """Append an audit record. Call inside the same transaction as the mutation."""
    return AuditEvent.objects.create(
        occurred_at=clock.now(),
        actor=actor if getattr(actor, "pk", None) else None,
        actor_kind=actor_kind or ("user" if getattr(actor, "pk", None) else "system"),
        action=action,
        object_type=obj.__class__.__name__ if obj is not None else "",
        object_id=str(getattr(obj, "pk", "") or ""),
        contact=contact,
        summary=summary[:300],
        data={k: redact_value(k, v) for k, v in (data or {}).items()},
        request_id=current_request_id(),
    )


def get_settings_row() -> WorkspaceSettings:
    row = WorkspaceSettings.objects.filter(pk=1).first()
    if row is None:
        row, _ = WorkspaceSettings.objects.get_or_create(pk=1, defaults={"policy": merged({})})
    return row


def get_policy() -> dict:
    return merged(get_settings_row().policy)


def update_policy(new_policy: dict, *, actor, expected_version: int, note: str = "") -> WorkspaceSettings:
    with transaction.atomic():
        updated = WorkspaceSettings.objects.filter(pk=1, version=expected_version).update(
            policy=merged(new_policy), version=expected_version + 1, updated_at=clock.now(), updated_by=actor
        )
        if updated != 1:
            raise ConflictError("Settings were changed by someone else. Reload and re-apply your change.")
        row = WorkspaceSettings.objects.get(pk=1)
        SettingsVersion.objects.create(
            version=row.version, policy=copy.deepcopy(row.policy), changed_by=actor, changed_at=clock.now(), note=note[:300]
        )
        audit("settings.updated", row, f"Workspace settings changed to version {row.version}", actor=actor, data={"note": note})
        return row
