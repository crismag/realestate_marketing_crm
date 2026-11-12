"""Workspace policy defaults.

Every value here is an IMPLEMENTATION DEFAULT chosen so the CRM can run. None of
them is an approved business policy (see context OQ-002, OQ-008, OQ-011, OQ-012).
All are editable on the Settings screen; each change is versioned and audited.
"""
from __future__ import annotations

import copy

INTERACTION_TYPES = [
    ("outbound_attempt", "Outbound attempt (no answer / left message)"),
    ("conversation", "Conversation (reached the customer)"),
    ("inbound_reply", "Inbound reply from customer"),
    ("meeting_tour", "Tour / viewing / consultation"),
    ("note", "Internal note (not customer contact)"),
]
CHANNELS = [
    ("phone", "Phone"),
    ("email", "Email"),
    ("sms", "SMS / chat"),
    ("in_person", "In person"),
    ("other", "Other"),
]

DEFAULT_POLICY: dict = {
    "workspace_name": "Realstate CRM",
    "timezone": "Asia/Shanghai",
    "currency": "USD",
    "lifecycle_labels": {"lead": "Lead", "prospect": "Prospect", "client": "Client"},
    # OQ-002 implementation default: a contact becomes a client when one of its
    # opportunities is marked won. Staff can still set lifecycle manually.
    "client_milestone": "opportunity_won",
    "opportunity_stages": [
        {"code": "new", "label": "New"},
        {"code": "qualification", "label": "Qualification"},
        {"code": "viewing", "label": "Viewing"},
        {"code": "proposal", "label": "Proposal / offer"},
        {"code": "decision", "label": "Decision"},
    ],
    "attention": {
        "after_tour_hours": 48,
        "inactivity_days": {"lead": 7, "prospect": 14, "client": 60},
        "missing_next_action_lifecycles": ["lead", "prospect"],
        "inquiry_response_hours": 24,
        "handover_pending_hours": 24,
        "pool_waiting_hours": 24,
        "escalation_overdue_hours": 72,
        # Activity types that count as follow-up after a tour and that reset
        # the inactivity clock. Profile views and notes never count.
        "followup_types": ["outbound_attempt", "conversation", "inbound_reply", "meeting_tour"],
        "contact_reset_types": ["outbound_attempt", "conversation", "inbound_reply", "meeting_tour"],
    },
    "notifications": {
        "digest_hour": 8,
        "attention_sweep_minutes": 15,
        "quiet_hours_start": 20,
        "quiet_hours_end": 8,
        "customer_frequency_cap_hours": 72,
        # User ids that receive escalations. Empty = routing gap shown in Automation.
        "escalation_recipient_ids": [],
    },
}


def merged(policy: dict | None) -> dict:
    """Return defaults overlaid with stored values so new keys get defaults."""
    result = copy.deepcopy(DEFAULT_POLICY)
    for key, value in (policy or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key].update(value)
        else:
            result[key] = value
    return result
