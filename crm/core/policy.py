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
    "workspace_name": "Real Estate CRM",
    # Company profile for this install (one install per customer company). Shown to staff and
    # available to customer email templates as {{ company_* }} placeholders.
    # Two-step sign-in (authenticator app) is optional per person unless the company requires it.
    "security": {"require_two_factor": False},
    "company": {"legal_name": "", "phone": "", "email": "", "website": "", "address": ""},
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
        # C-R2 implementation default: flag open opportunities whose stage has not changed for this many
        # days (0 = off), and ones still open after their expected close date.
        "stalled_opportunity_days": 21,
        "flag_past_expected_close": True,
        # Activity types that count as follow-up after a tour and that reset
        # the inactivity clock. Profile views and notes never count.
        "followup_types": ["outbound_attempt", "conversation", "inbound_reply", "meeting_tour"],
        "contact_reset_types": ["outbound_attempt", "conversation", "inbound_reply", "meeting_tour"],
    },
    # C-R6 implementation default: also match +tag email variants and multi-word names in any order.
    # False = exact email/phone/name only (the original rule).
    "duplicate_matching": {"extended": True},
    # C-R3 implementation default: after an interaction is logged, pre-fill (never create) a follow-up task.
    # Keyed by interaction type; hours = suggested due time from now. Types not listed get no suggestion.
    "followup_suggestions": {
        "enabled": True,
        "by_kind": {
            "meeting_tour": {"title": "Follow up after the tour", "hours": 24},
            "conversation": {"title": "Follow up on the conversation", "hours": 72},
            "outbound_attempt": {"title": "Try again to reach the customer", "hours": 24},
            "inbound_reply": {"title": "Respond to the customer's reply", "hours": 4},
        },
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
