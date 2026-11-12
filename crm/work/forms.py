from django import forms
from django.contrib.auth import get_user_model

from crm.core.forms import Form, LocalDateTimeField

from .models import Pool, Task

User = get_user_model()


class TaskForm(Form):
    title = forms.CharField(max_length=200, label="Next action")
    kind = forms.ChoiceField(choices=Task.KINDS, initial="follow_up", label="Type")
    assignee = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True).order_by("full_name"),
                                      help_text="Assigning a task does not transfer the client.")
    due_at = LocalDateTimeField(required=False, label="Due")
    critical = forms.BooleanField(required=False, label="Critical")
    description = forms.CharField(required=False, widget=forms.Textarea, label="Details")


class ReplanForm(Form):
    due_at = LocalDateTimeField(label="New due time")
    reason = forms.CharField(max_length=200)
    version = forms.IntegerField(widget=forms.HiddenInput)


class HandoverForm(Form):
    kind = forms.ChoiceField(choices=[("transfer", "Transfer to a colleague"), ("release", "Release to a shared pool")],
                             widget=forms.RadioSelect, initial="transfer")
    recipient = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True).order_by("full_name"), required=False,
                                       label="Colleague")
    pool = forms.ModelChoiceField(queryset=Pool.objects.filter(active=True), required=False,
                                  help_text="The pool coordinator must accept the release.")
    reason = forms.CharField(max_length=300)
    context = forms.CharField(required=False, widget=forms.Textarea, label="Context for the recipient",
                              help_text="Where things stand and what should happen next")
    version = forms.IntegerField(widget=forms.HiddenInput)

    def __init__(self, *args, tasks=(), exclude_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kind"].widget.attrs.pop("class", None)
        if exclude_user is not None:
            self.fields["recipient"].queryset = self.fields["recipient"].queryset.exclude(pk=exclude_user.pk)
        self.task_fields = []
        for task in tasks:
            name = f"task_{task.pk}"
            self.fields[name] = forms.ChoiceField(
                choices=[("", "Choose…"), ("keep", f"Keep with {task.assignee}"), ("transfer", "Move to the new handler on acceptance")],
                label=f"Task: {task.title}", help_text=f"Due {task.due_at:%Y-%m-%d %H:%M} UTC" if task.due_at else "No due date",
            )
            self.fields[name].widget.attrs.update({"class": "cg-select", "data-size": "md", "data-color": "default"})
            self.task_fields.append((task, name))

    def clean(self):
        data = super().clean()
        if data.get("kind") == "transfer" and not data.get("recipient"):
            self.add_error("recipient", "Choose the colleague.")
        if data.get("kind") == "release" and not data.get("pool"):
            self.add_error("pool", "Choose the pool.")
        return data

    def dispositions(self):
        return {task.pk: self.cleaned_data[name] for task, name in self.task_fields}
