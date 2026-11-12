"""Idempotent reference data: rule catalog, templates, workspace settings, default sources."""
from __future__ import annotations

DEFAULT_SOURCES = [
    ("website", "Website form", "website"),
    ("walk-in", "Walk-in", "walk_in"),
    ("referral", "Referral", "referral"),
    ("roadshow", "Roadshow / event", "roadshow"),
    ("social", "Social media", "social"),
    ("search", "Search", "search"),
    ("other", "Other", "other"),
]


def ensure_reference_data(apps=None):
    from crm.automation.catalog import RULES, TEMPLATES
    from crm.core.policy import merged

    def model(label, name):
        if apps is not None:
            return apps.get_model(label, name)
        from django.apps import apps as global_apps

        return global_apps.get_model(label, name)

    Rule = model("automation", "Rule")
    RuleVersion = model("automation", "RuleVersion")
    MessageTemplate = model("comms", "MessageTemplate")
    WorkspaceSettings = model("core", "WorkspaceSettings")
    SettingsVersion = model("core", "SettingsVersion")
    Source = model("contacts", "Source")

    for spec in RULES:
        defaults = {k: v for k, v in spec.items() if k != "key"}
        defaults.setdefault("config", {"template": "inquiry-ack", "delay_minutes": 0} if spec["key"] == "customer-followup"
                            else {"template": "onboarding"} if spec["key"] == "onboard" else {})
        rule, created = Rule.objects.get_or_create(key=spec["key"], defaults=defaults)
        if created:
            RuleVersion.objects.create(rule=rule, version=1, enabled=rule.enabled, config=rule.config,
                                       note="Initial catalog version")
        else:
            # Keep descriptive text current without touching enabled/config/version.
            Rule.objects.filter(pk=rule.pk).update(**{k: v for k, v in defaults.items()
                                                       if k in ("name", "trigger", "conditions", "action", "stop_policy", "audience")})
    for spec in TEMPLATES:
        MessageTemplate.objects.get_or_create(key=spec["key"], defaults={k: v for k, v in spec.items() if k != "key"})
    if not WorkspaceSettings.objects.filter(pk=1).exists():
        policy = merged({})
        WorkspaceSettings.objects.create(pk=1, policy=policy, version=1)
        SettingsVersion.objects.get_or_create(version=1, defaults={"policy": policy, "note": "Implementation defaults"})
    for code, label, kind in DEFAULT_SOURCES:
        Source.objects.get_or_create(code=code, defaults={"label": label, "kind": kind})
