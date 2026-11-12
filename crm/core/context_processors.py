def workspace(request):
    policy = getattr(request, "crm_policy", None)
    context = {"workspace_name": (policy or {}).get("workspace_name", "Realstate CRM")}
    if policy is not None:
        context["crm_policy"] = policy
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from crm.automation.models import Notification

        context["unread_notifications"] = Notification.objects.filter(
            recipient=user, read_at__isnull=True, dismissed_at__isnull=True
        ).count()
    return context
