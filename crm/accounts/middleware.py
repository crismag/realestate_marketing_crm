from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """Users with a temporary password can only change it or sign out. When the company requires
    two-step sign-in, users without it can only set it up or sign out."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.must_change_password:
            allowed = {reverse("accounts:password_change"), reverse("accounts:logout")}
            if request.path not in allowed and not request.path.startswith("/static/"):
                return redirect("accounts:password_change")
            # Finish the password change first; the two-step requirement applies on the next page.
            return self.get_response(request)
        if user is not None and user.is_authenticated and not user.two_factor_enabled:
            policy = getattr(request, "crm_policy", None)
            if policy is None:
                from crm.core.services import get_policy

                policy = get_policy()
            if policy.get("security", {}).get("require_two_factor"):
                allowed = {reverse("accounts:two_factor"), reverse("accounts:logout")}
                if request.path not in allowed and not request.path.startswith("/static/"):
                    return redirect("accounts:two_factor")
        return self.get_response(request)
