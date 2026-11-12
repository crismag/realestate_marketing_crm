from django import forms
from django.contrib.auth import get_user_model

from crm.core.forms import Form, LocalDateTimeField
from crm.core.policy import CHANNELS, INTERACTION_TYPES
from crm.work.models import Pool

from .models import LIFECYCLES, Contact, Source

User = get_user_model()


def active_users():
    return User.objects.filter(is_active=True).order_by("full_name")


class ContactFieldsForm(Form):
    display_name = forms.CharField(max_length=150, label="Name")
    email = forms.EmailField(required=False, max_length=254)
    phone = forms.CharField(required=False, max_length=40)
    source = forms.ModelChoiceField(queryset=Source.objects.filter(active=True), required=False, label="Acquisition source")
    source_detail = forms.CharField(required=False, max_length=200, label="Source detail",
                                    help_text="Campaign, event, page or referral details")
    introducer = forms.ModelChoiceField(queryset=active_users(), required=False, label="Introduced by (staff)",
                                        help_text="Referral credit only. Does not make them responsible.")
    interests = forms.CharField(required=False, widget=forms.Textarea, label="Interests / requirements")
    preferred_channel = forms.ChoiceField(choices=[("", "No preference")] + CHANNELS, required=False)
    next_contact_agreed_at = LocalDateTimeField(required=False, label="Customer asked to be contacted on",
                                                help_text="Suppresses routine inactivity reminders until then; urgent items still show.")
    notes = forms.CharField(required=False, widget=forms.Textarea)

    def clean(self):
        data = super().clean()
        phone = data.get("phone", "")
        if phone and sum(ch.isdigit() for ch in phone) < 6:
            self.add_error("phone", "Enter a phone number with at least 6 digits.")
        return data


class CaptureForm(ContactFieldsForm):
    destination = forms.ChoiceField(choices=[("me", "I am responsible"), ("pool", "Put in a shared pool")],
                                    widget=forms.RadioSelect, initial="me", label="Responsibility")
    pool = forms.ModelChoiceField(queryset=Pool.objects.filter(active=True), required=False)
    inquiry_message = forms.CharField(required=False, widget=forms.Textarea, label="Inquiry (optional)",
                                      help_text="What the customer asked for. Creates an inquiry awaiting response.")
    inquiry_channel = forms.ChoiceField(choices=CHANNELS, initial="phone", required=False, label="Inquiry channel")
    confirm_new = forms.BooleanField(required=False, label="This is a different person; create a new contact anyway")

    field_order = ["display_name", "email", "phone", "source", "source_detail", "introducer", "destination", "pool",
                   "inquiry_message", "inquiry_channel", "interests", "preferred_channel", "next_contact_agreed_at", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["destination"].widget.attrs.pop("class", None)

    def clean(self):
        data = super().clean()
        if data.get("destination") == "pool" and not data.get("pool"):
            self.add_error("pool", "Choose the pool.")
        return data


class LifecycleForm(Form):
    lifecycle = forms.ChoiceField(choices=LIFECYCLES)
    disposition = forms.ChoiceField(choices=Contact._meta.get_field("disposition").choices)
    reason = forms.CharField(required=False, max_length=200)
    version = forms.IntegerField(widget=forms.HiddenInput)


class InquiryForm(Form):
    message = forms.CharField(widget=forms.Textarea, label="Inquiry")
    channel = forms.ChoiceField(choices=CHANNELS, initial="phone")
    source = forms.ModelChoiceField(queryset=Source.objects.filter(active=True), required=False,
                                    help_text="Leave empty to use the contact's acquisition source")
    received_at = LocalDateTimeField(required=False, label="Received at", help_text="Leave empty for now")


class InteractionForm(Form):
    kind = forms.ChoiceField(choices=INTERACTION_TYPES, label="What happened")
    channel = forms.ChoiceField(choices=CHANNELS, initial="phone")
    summary = forms.CharField(widget=forms.Textarea)
    occurred_at = LocalDateTimeField(required=False, label="When", help_text="Leave empty for now. Future times are not allowed.")
    inquiry = forms.ModelChoiceField(queryset=None, required=False, label="Responds to inquiry",
                                     help_text="Marks the inquiry responded (attempts, conversations and tours count)")

    def __init__(self, *args, contact=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = contact.inquiries.filter(status="awaiting") if contact else None
        self.fields["inquiry"].queryset = qs if qs is not None else self.fields["inquiry"].queryset
        if qs is not None and qs.exists():
            self.fields["inquiry"].initial = qs.order_by("received_at").first()


class OpportunityForm(Form):
    title = forms.CharField(max_length=200)
    stage = forms.ChoiceField(choices=[])
    amount = forms.DecimalField(required=False, min_value=0, max_digits=14, decimal_places=2,
                                help_text="Potential transaction value (not earnings)")
    expected_close = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    version = forms.IntegerField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, stages=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["stage"].choices = [(s["code"], s["label"]) for s in stages]


class OpportunityOutcomeForm(Form):
    outcome = forms.ChoiceField(choices=[("won", "Won"), ("lost", "Lost"), ("open", "Reopen")])
    reason = forms.CharField(required=False, max_length=200)
    version = forms.IntegerField(widget=forms.HiddenInput)

    def clean(self):
        data = super().clean()
        if data.get("outcome") == "lost" and not data.get("reason"):
            self.add_error("reason", "Record why it was lost.")
        return data
