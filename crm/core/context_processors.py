def workspace(request):
    policy = getattr(request, "crm_policy", None)
    if policy is None:
        # Anonymous pages (sign-in) still show the company's name.
        from crm.core.services import get_policy

        try:
            policy = get_policy()
        except Exception:  # noqa: BLE001 - e.g. before the first migration
            policy = None
    context = {"workspace_name": (policy or {}).get("workspace_name", "Real Estate CRM")}
    if policy is not None:
        context["crm_policy"] = policy
    from crm.core.models import BrandLogo

    try:
        context["logo_version"] = BrandLogo.objects.filter(pk=1).values_list("sha256", flat=True).first()
    except Exception:  # noqa: BLE001 - before the first migration
        context["logo_version"] = None
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from crm.automation.models import Notification

        context["unread_notifications"] = Notification.objects.filter(
            recipient=user, read_at__isnull=True, dismissed_at__isnull=True
        ).count()
    return context
