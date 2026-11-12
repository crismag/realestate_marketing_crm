"""Form helpers: CrisGen classes on widgets, explicit fields only (no mass assignment)."""
from __future__ import annotations

import datetime as dt

from django import forms
from django.utils import timezone


class CrisGenMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            attrs = widget.attrs
            if isinstance(widget, forms.RadioSelect):
                attrs.setdefault("class", "cg-radio")
                attrs.setdefault("data-color", "primary")
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                attrs.setdefault("class", "cg-checkbox")
                attrs.setdefault("data-color", "primary")
            elif isinstance(widget, forms.CheckboxInput):
                attrs.setdefault("class", "cg-checkbox")
                attrs.setdefault("data-color", "primary")
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                attrs.setdefault("class", "cg-select")
                attrs.setdefault("data-size", "md")
                attrs.setdefault("data-color", "default")
            elif isinstance(widget, forms.Textarea):
                attrs.setdefault("class", "cg-textarea")
                attrs.setdefault("data-size", "md")
                attrs.setdefault("data-color", "default")
                attrs.setdefault("rows", 3)
            elif not isinstance(widget, forms.HiddenInput):
                attrs.setdefault("class", "cg-input")
                attrs.setdefault("data-size", "md")
                attrs.setdefault("data-color", "default")
            if field.help_text:
                attrs.setdefault("aria-describedby", f"id_{self.add_prefix(name)}_help")

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs["data-color"] = "error"
                self.fields[name].widget.attrs["aria-invalid"] = "true"


class LocalDateTimeField(forms.DateTimeField):
    """<input type=datetime-local> interpreted in the active (workspace) timezone, stored as UTC."""

    widget = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
    input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"]

    def prepare_value(self, value):
        if isinstance(value, dt.datetime) and timezone.is_aware(value):
            return timezone.localtime(value).strftime("%Y-%m-%dT%H:%M")
        return value


class Form(CrisGenMixin, forms.Form):
    pass


class ModelForm(CrisGenMixin, forms.ModelForm):
    pass
