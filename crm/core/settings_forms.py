import zoneinfo

from django import forms
from django.contrib.auth import get_user_model

from crm.accounts.models import Team
from crm.contacts.models import Source
from crm.core.policy import INTERACTION_TYPES

from .forms import Form

User = get_user_model()
HOURS = [(h, f"{h:02d}:00") for h in range(24)]


class PolicyForm(Form):
    timezone = forms.CharField(max_length=64, help_text="IANA name, e.g. Asia/Shanghai, Asia/Manila, UTC")
    currency = forms.RegexField(regex=r"^[A-Z]{3}$", max_length=3, help_text="ISO 4217 code, e.g. USD, PHP")
    label_lead = forms.CharField(max_length=40, label="Label for lead")
    label_prospect = forms.CharField(max_length=40, label="Label for prospect")
    label_client = forms.CharField(max_length=40, label="Label for client")
    stages = forms.CharField(widget=forms.Textarea, label="Opportunity stages",
                             help_text="One per line as code:Label. Won/Lost are outcomes, not stages. Codes must stay stable.")
    after_tour_hours = forms.IntegerField(min_value=1, max_value=24 * 60, label="Follow up after a tour within (hours)")
    inactivity_lead = forms.IntegerField(min_value=0, max_value=3650, label="Lead contact cadence (days, 0 = off)")
    inactivity_prospect = forms.IntegerField(min_value=0, max_value=3650, label="Prospect contact cadence (days, 0 = off)")
    inactivity_client = forms.IntegerField(min_value=0, max_value=3650, label="Client contact cadence (days, 0 = off)")
    inquiry_response_hours = forms.IntegerField(min_value=1, max_value=24 * 30, label="Inquiry response target (hours)")
    handover_pending_hours = forms.IntegerField(min_value=1, max_value=24 * 30, label="Remind about pending handovers after (hours)")
    pool_waiting_hours = forms.IntegerField(min_value=1, max_value=24 * 30, label="Flag pool items waiting longer than (hours)")
    escalation_overdue_hours = forms.IntegerField(min_value=1, max_value=24 * 90, label="Escalate tasks overdue by (hours)")
    stalled_opportunity_days = forms.IntegerField(min_value=0, max_value=3650,
                                                  label="Flag opportunities whose stage has not changed for (days, 0 = off)")
    flag_past_expected_close = forms.BooleanField(required=False, label="Flag open opportunities past their expected close date")
    followup_suggestions_enabled = forms.BooleanField(required=False, label="Suggest a follow-up task after logging an interaction")
    extended_duplicate_matching = forms.BooleanField(
        required=False, label="Wider duplicate check (+tag emails, names in any order)")
    contact_reset_types = forms.MultipleChoiceField(
        choices=[c for c in INTERACTION_TYPES if c[0] != "note"], widget=forms.CheckboxSelectMultiple,
        label="Interactions that count as contact (reset inactivity and after-tour follow-up)")
    digest_hour = forms.TypedChoiceField(choices=HOURS, coerce=int, label="Daily digest time")
    attention_sweep_minutes = forms.IntegerField(min_value=1, max_value=1440, label="Attention sweep every (minutes)")
    quiet_hours_start = forms.TypedChoiceField(choices=HOURS, coerce=int, label="Customer quiet hours start")
    quiet_hours_end = forms.TypedChoiceField(choices=HOURS, coerce=int, label="Customer quiet hours end")
    customer_frequency_cap_hours = forms.IntegerField(min_value=0, max_value=24 * 30, label="Min hours between automated customer emails")
    escalation_recipients = forms.ModelMultipleChoiceField(queryset=User.objects.filter(is_active=True), required=False,
                                                           widget=forms.CheckboxSelectMultiple)
    note = forms.CharField(max_length=200, required=False, label="Change note")
    version = forms.IntegerField(widget=forms.HiddenInput)

    def clean_timezone(self):
        value = self.cleaned_data["timezone"].strip()
        try:
            zoneinfo.ZoneInfo(value)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError):
            raise forms.ValidationError("Unknown timezone.")
        return value

    def clean_stages(self):
        stages, seen = [], set()
        for line in self.cleaned_data["stages"].splitlines():
            line = line.strip()
            if not line:
                continue
            code, _, label = line.partition(":")
            code, label = code.strip().lower(), label.strip() or code.strip()
            if not code.replace("_", "").isalnum() or len(code) > 40:
                raise forms.ValidationError(f"Invalid stage code '{code}'. Use letters, numbers and underscores.")
            if code in seen or code in ("won", "lost"):
                raise forms.ValidationError(f"Stage code '{code}' is duplicated or reserved.")
            seen.add(code)
            stages.append({"code": code, "label": label[:60]})
        if not stages:
            raise forms.ValidationError("Keep at least one stage.")
        return stages

    @classmethod
    def initial_from(cls, policy, version):
        a, n, labels = policy["attention"], policy["notifications"], policy["lifecycle_labels"]
        return {
            "timezone": policy["timezone"], "currency": policy["currency"],
            "label_lead": labels["lead"], "label_prospect": labels["prospect"], "label_client": labels["client"],
            "stages": "\n".join(f"{s['code']}:{s['label']}" for s in policy["opportunity_stages"]),
            "after_tour_hours": a["after_tour_hours"], "inactivity_lead": a["inactivity_days"].get("lead", 0),
            "inactivity_prospect": a["inactivity_days"].get("prospect", 0), "inactivity_client": a["inactivity_days"].get("client", 0),
            "inquiry_response_hours": a["inquiry_response_hours"], "handover_pending_hours": a["handover_pending_hours"],
            "pool_waiting_hours": a["pool_waiting_hours"], "escalation_overdue_hours": a["escalation_overdue_hours"],
            "stalled_opportunity_days": a.get("stalled_opportunity_days", 0),
            "flag_past_expected_close": a.get("flag_past_expected_close", False),
            "followup_suggestions_enabled": policy.get("followup_suggestions", {}).get("enabled", False),
            "extended_duplicate_matching": policy.get("duplicate_matching", {}).get("extended", False),
            "contact_reset_types": a["contact_reset_types"], "digest_hour": n["digest_hour"],
            "attention_sweep_minutes": n["attention_sweep_minutes"], "quiet_hours_start": n["quiet_hours_start"],
            "quiet_hours_end": n["quiet_hours_end"], "customer_frequency_cap_hours": n["customer_frequency_cap_hours"],
            "escalation_recipients": User.objects.filter(pk__in=n.get("escalation_recipient_ids") or []),
            "version": version,
        }

    def to_policy(self, current):
        d = self.cleaned_data
        policy = dict(current)
        policy.update({"timezone": d["timezone"], "currency": d["currency"],
                       "lifecycle_labels": {"lead": d["label_lead"], "prospect": d["label_prospect"], "client": d["label_client"]},
                       "opportunity_stages": d["stages"]})
        policy["attention"] = {**current["attention"],
                               "after_tour_hours": d["after_tour_hours"],
                               "inactivity_days": {"lead": d["inactivity_lead"], "prospect": d["inactivity_prospect"],
                                                   "client": d["inactivity_client"]},
                               "inquiry_response_hours": d["inquiry_response_hours"],
                               "handover_pending_hours": d["handover_pending_hours"],
                               "pool_waiting_hours": d["pool_waiting_hours"],
                               "escalation_overdue_hours": d["escalation_overdue_hours"],
                               "stalled_opportunity_days": d["stalled_opportunity_days"],
                               "flag_past_expected_close": d["flag_past_expected_close"],
                               "contact_reset_types": list(d["contact_reset_types"]),
                               "followup_types": list(d["contact_reset_types"])}
        policy["setup"] = {**current.get("setup", {}), "settings_reviewed": True}
        policy["followup_suggestions"] = {**current.get("followup_suggestions", {}),
                                          "enabled": d["followup_suggestions_enabled"]}
        policy["duplicate_matching"] = {**current.get("duplicate_matching", {}),
                                        "extended": d["extended_duplicate_matching"]}
        policy["notifications"] = {**current["notifications"], "digest_hour": d["digest_hour"],
                                   "attention_sweep_minutes": d["attention_sweep_minutes"],
                                   "quiet_hours_start": d["quiet_hours_start"], "quiet_hours_end": d["quiet_hours_end"],
                                   "customer_frequency_cap_hours": d["customer_frequency_cap_hours"],
                                   "escalation_recipient_ids": [u.pk for u in d["escalation_recipients"]]}
        return policy


class PoolForm(Form):
    name = forms.CharField(max_length=100)
    team = forms.ModelChoiceField(queryset=Team.objects.filter(active=True), required=False)
    coordinator = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True), required=False,
                                         help_text="Receives pool attention and accepts releases. Without one, alerts show a routing gap.")
    backup_coordinator = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True), required=False)
    active = forms.BooleanField(required=False, initial=True)


class TeamForm(Form):
    name = forms.CharField(max_length=100)
    active = forms.BooleanField(required=False, initial=True)


class SourceForm(Form):
    label = forms.CharField(max_length=100)
    code = forms.SlugField(max_length=50, required=False,
                           help_text="Stable code used in exports and the intake API. Leave empty to derive it from the label.")
    kind = forms.ChoiceField(choices=Source.KINDS)
    active = forms.BooleanField(required=False, initial=True)

    def clean(self):
        data = super().clean()
        if not data.get("code") and data.get("label"):
            from django.utils.text import slugify

            data["code"] = slugify(data["label"])[:50] or "source"
        if not data.get("code"):
            self.add_error("code", "Enter a code or a label.")
        return data


LOGO_MAX_BYTES = 512 * 1024
LOGO_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)


def sniff_logo(data: bytes) -> str | None:
    """Accept PNG, JPEG and WebP by their magic bytes. SVG is refused (it can carry script)."""
    for magic, ctype in LOGO_SIGNATURES:
        if data.startswith(magic):
            return ctype
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


class CompanyForm(Form):
    workspace_name = forms.CharField(max_length=80, label="Name shown in the app",
                                     help_text="Appears in the menu, the sign-in page and customer emails.")
    legal_name = forms.CharField(max_length=160, required=False, label="Registered company name")
    phone = forms.CharField(max_length=40, required=False, label="Office phone")
    email = forms.EmailField(max_length=160, required=False, label="Office email")
    website = forms.URLField(max_length=200, required=False, assume_scheme="https", label="Website")
    address = forms.CharField(max_length=300, required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Office address")
    logo = forms.FileField(required=False, label="Logo", help_text="PNG, JPEG or WebP, up to 512 KB. Shown in the menu and sign-in page.")
    remove_logo = forms.BooleanField(required=False, label="Remove the current logo")
    note = forms.CharField(max_length=200, required=False, label="Change note")
    version = forms.IntegerField(widget=forms.HiddenInput)

    def clean_logo(self):
        f = self.cleaned_data.get("logo")
        if not f:
            return None
        if f.size > LOGO_MAX_BYTES:
            raise forms.ValidationError("The logo must be 512 KB or smaller.")
        data = f.read(LOGO_MAX_BYTES + 1)
        ctype = sniff_logo(data)
        if ctype is None:
            raise forms.ValidationError("Upload a PNG, JPEG or WebP image.")
        return {"data": data, "content_type": ctype}

    @classmethod
    def initial_from(cls, policy, version):
        c = policy.get("company") or {}
        return {"workspace_name": policy["workspace_name"], **{k: c.get(k, "") for k in ("legal_name", "phone", "email",
                                                                                           "website", "address")},
                "version": version}

    def to_policy(self, current):
        d = self.cleaned_data
        policy = dict(current)
        policy["workspace_name"] = d["workspace_name"]
        policy["company"] = {k: d[k].strip() for k in ("legal_name", "phone", "email", "website", "address")}
        return policy
