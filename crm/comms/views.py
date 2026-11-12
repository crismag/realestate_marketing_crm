from django import forms
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from crm.core import clock
from crm.core.forms import Form
from crm.core.services import audit, get_policy
from crm.core.web import paginate, run_action

from . import services
from .models import MessageTemplate, OutboundMessage


def message_list(request):
    qs = OutboundMessage.objects.select_related("contact", "template", "rule")
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)
    page, querystring = paginate(request, qs, per_page=30)
    counts = {s: OutboundMessage.objects.filter(status=s).count() for s, _ in OutboundMessage.STATUSES}
    return render(request, "comms/list.html", {"page": page, "querystring": querystring, "status": status,
                                               "statuses": OutboundMessage.STATUSES, "counts": counts,
                                               "templates": MessageTemplate.objects.all()})


def message_detail(request, pk):
    msg = get_object_or_404(OutboundMessage.objects.select_related("contact", "template", "rule"), pk=pk)
    return render(request, "comms/detail.html", {"msg": msg})


@require_POST
def message_retry(request, pk):
    msg = get_object_or_404(OutboundMessage, pk=pk)
    response, _ = run_action(request, lambda: services.retry_message(msg, actor=request.user),
                             success="Retry queued. The sandbox transport will capture it on the next worker pass.",
                             redirect_to=f"/messages/{pk}/")
    return response


@require_POST
def message_resolve(request, pk):
    msg = get_object_or_404(OutboundMessage, pk=pk)
    response, _ = run_action(request, lambda: services.resolve_uncertain(msg, actor=request.user,
                                                                         outcome=request.POST.get("outcome", ""),
                                                                         note=request.POST.get("note", "")),
                             success="Outcome recorded.", redirect_to=f"/messages/{pk}/")
    return response


class TemplateForm(Form):
    name = forms.CharField(max_length=120)
    subject = forms.CharField(max_length=200)
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 8}),
                           help_text="Plain text. Placeholders: {{ customer_name }}, {{ handler_name }}, {{ workspace_name }}")
    active = forms.BooleanField(required=False)
    version = forms.IntegerField(widget=forms.HiddenInput)

    def clean(self):
        data = super().clean()
        import re

        for field in ("subject", "body"):
            for name in re.findall(r"\{\{\s*([a-z_]+)\s*\}\}", data.get(field, "") or ""):
                if name not in MessageTemplate.ALLOWED_FIELDS:
                    self.add_error(field, f"Unknown placeholder '{name}'.")
        return data


def template_edit(request, pk):
    tpl = get_object_or_404(MessageTemplate, pk=pk)
    form = TemplateForm(request.POST or None, initial={"name": tpl.name, "subject": tpl.subject, "body": tpl.body,
                                                       "active": tpl.active, "version": tpl.version})
    preview = None
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        if request.POST.get("action") == "preview":
            values = {"customer_name": "Sample Customer", "handler_name": request.user.full_name,
                      "workspace_name": get_policy()["workspace_name"]}
            preview = {"subject": services.render_template(d["subject"], values),
                       "body": services.render_template(d["body"], values)}
        else:
            with transaction.atomic():
                updated = MessageTemplate.objects.filter(pk=tpl.pk, version=d["version"]).update(
                    name=d["name"], subject=d["subject"], body=d["body"], active=d["active"], version=d["version"] + 1,
                    updated_at=clock.now(), updated_by=request.user)
                if updated != 1:
                    form.add_error(None, "This template was changed by someone else. Reload and re-apply your change.")
                else:
                    audit("template.updated", tpl, f"Template '{d['name']}' saved as v{d['version'] + 1}", actor=request.user)
            if not form.errors:
                messages.success(request, "Template saved. Messages already captured keep the text they were sent with.")
                return redirect("comms:list")
    return render(request, "comms/template.html", {"form": form, "tpl": tpl, "preview": preview})
