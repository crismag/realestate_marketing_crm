def workspace(request):
    policy = getattr(request, "crm_policy", None)
    if policy is None:
        return {"workspace_name": "Realstate CRM"}
    return {"workspace_name": policy.get("workspace_name", "Realstate CRM"), "crm_policy": policy}
