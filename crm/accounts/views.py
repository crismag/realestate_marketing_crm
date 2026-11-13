from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from crm.core import clock
from crm.core.forms import CrisGenMixin
from crm.core.services import audit, get_policy
from crm.work.models import Assignment, Task

from . import services, totp
from .forms import LoginForm, PasswordConfirmForm, ResetPasswordForm, SecondFactorForm, UserCreateForm, UserEditForm
from .models import User


def client_ip(request) -> str:
    return request.META.get("REMOTE_ADDR", "")


@login_not_required
def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:today")
    form = LoginForm(request.POST or None)
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        ip = client_ip(request)
        remaining = services.lockout_remaining(email, ip)
        if remaining:
            minutes = int(remaining.total_seconds() // 60) + 1
            form.add_error(None, f"Too many failed sign-in attempts. Try again in about {minutes} minute(s).")
        else:
            user = authenticate(request, email=email, password=form.cleaned_data["password"])
            if user is None:
                services.record_failure(email, ip)
                form.add_error(None, "Email or password is incorrect, or the account is inactive.")
            else:
                if user.two_factor_enabled:
                    # Failure counters are cleared only after the second factor succeeds (login_verify).
                    # Password was right; the session only remembers who is half-way through signing in.
                    request.session.cycle_key()
                    request.session[PENDING_2FA] = {"uid": user.pk, "at": clock.now().timestamp(), "next": next_url}
                    return redirect("accounts:login_verify")
                services.record_success(email, ip)
                return _complete_login(request, user, next_url)
    return render(request, "accounts/login.html", {"form": form, "next": next_url})


PENDING_2FA = "pending_two_factor"
PENDING_2FA_SECONDS = 300


def _complete_login(request, user, next_url: str, *, method: str = "password"):
    login(request, user)  # rotates the session key
    audit("auth.login", user, "Signed in" + (" with two-step sign-in" if method != "password" else ""), actor=user,
          data={"method": method})
    if user.must_change_password:
        messages.info(request, "Please choose a new password before continuing.")
        return redirect("accounts:password_change")
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
        return redirect(next_url)
    return redirect("core:today")


@login_not_required
def login_verify(request):
    pending = request.session.get(PENDING_2FA)
    if not pending or clock.now().timestamp() - pending["at"] > PENDING_2FA_SECONDS:
        request.session.pop(PENDING_2FA, None)
        messages.info(request, "Please sign in again.")
        return redirect("accounts:login")
    user = User.objects.filter(pk=pending["uid"], is_active=True).first()
    if user is None or not user.two_factor_enabled:
        request.session.pop(PENDING_2FA, None)
        return redirect("accounts:login")
    form = SecondFactorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ip = client_ip(request)
        remaining = services.lockout_remaining(user.email, ip)
        if remaining:
            form.add_error(None, f"Too many failed attempts. Try again in about {int(remaining.total_seconds() // 60) + 1} minute(s).")
        elif services.verify_second_factor(user, form.cleaned_data["code"]):
            request.session.pop(PENDING_2FA, None)
            services.record_success(user.email, ip)
            return _complete_login(request, user, pending.get("next", ""), method="two_factor")
        else:
            services.record_failure(user.email, ip)
            form.add_error("code", "That code is not right. Use the current code from your app, or a recovery code.")
    return render(request, "accounts/login_verify.html", {"form": form})


def two_factor(request):
    """Turn two-step sign-in on or off for yourself."""
    user = request.user
    recovery_codes = None
    if user.two_factor_enabled:
        form = PasswordConfirmForm(request.POST or None)
        if request.method == "POST" and request.POST.get("action") == "disable" and form.is_valid():
            if not user.check_password(form.cleaned_data["password"]):
                form.add_error("password", "Password is incorrect.")
            elif get_policy().get("security", {}).get("require_two_factor"):
                form.add_error(None, "Your company requires two-step sign-in, so it cannot be turned off.")
            else:
                services.disable_two_factor(user, actor=user)
                messages.success(request, "Two-step sign-in is off.")
                return redirect("accounts:two_factor")
        return render(request, "accounts/two_factor.html", {"form": form, "enabled": True,
                                                             "codes_left": len(user.recovery_code_hashes)})
    secret = request.session.get("two_factor_setup_secret") or totp.new_secret()
    request.session["two_factor_setup_secret"] = secret
    form = SecondFactorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        recovery_codes = services.enable_two_factor(user, secret=secret, code=form.cleaned_data["code"])
        if recovery_codes is None:
            form.add_error("code", "That code is not right. Check the time on your phone and try the newest code.")
        else:
            request.session.pop("two_factor_setup_secret", None)
            messages.success(request, "Two-step sign-in is on.")
            return render(request, "accounts/two_factor.html", {"enabled": True, "recovery_codes": recovery_codes,
                                                                 "codes_left": len(recovery_codes)})
    issuer = get_policy()["workspace_name"]
    uri = totp.provisioning_uri(secret, account=user.email, issuer=issuer)
    return render(request, "accounts/two_factor.html", {
        "form": form, "enabled": False, "qr_svg": mark_safe(totp.qr_svg(uri)),  # noqa: S308 - segno output: path data only, no user text
        "secret_groups": " ".join(secret[i:i + 4] for i in range(0, len(secret), 4)),
    })


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        audit("auth.logout", request.user, "Signed out", actor=request.user)
    logout(request)  # flushes the session server-side
    messages.info(request, "You have signed out.")
    return redirect("accounts:login")


class StyledPasswordChangeForm(CrisGenMixin, PasswordChangeForm):
    pass


def password_change(request):
    form = StyledPasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            User.objects.filter(pk=user.pk).update(must_change_password=False)
            audit("auth.password_changed", user, "Password changed", actor=user)
        update_session_auth_hash(request, user)
        request.session.cycle_key()
        messages.success(request, "Password changed.")
        return redirect("core:today")
    return render(request, "accounts/password_change.html", {"form": form})


def _require_admin(request):
    if not request.user.is_staff:
        raise PermissionDenied("Only workspace administrators can manage user accounts.")


def users_list(request):
    users = User.objects.prefetch_related("teams").order_by("-is_active", "full_name")
    return render(request, "accounts/users.html", {"users": users, "can_admin": request.user.is_staff})


def user_create(request):
    _require_admin(request)
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        with transaction.atomic():
            user = User.objects.create_user(d["email"], d["full_name"], d["temporary_password"], title=d["title"],
                                            is_staff=d["is_staff"], must_change_password=True)
            user.teams.set(d["teams"])
            audit("user.created", user, f"User {user.email} created", actor=request.user)
        messages.success(request, f"{user.full_name} can now sign in and must change the temporary password.")
        return redirect("accounts:users")
    return render(request, "accounts/user_form.html", {"form": form, "title": "Add user"})


def user_edit(request, pk):
    _require_admin(request)
    target = get_object_or_404(User, pk=pk)
    initial = {"full_name": target.full_name, "title": target.title, "teams": target.teams.all(),
               "is_active": target.is_active, "is_staff": target.is_staff}
    form = UserEditForm(request.POST or None, initial=initial)
    reset = ResetPasswordForm(user=target)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        if target.pk == request.user.pk and (not d["is_active"] or not d["is_staff"]):
            form.add_error(None, "You cannot deactivate yourself or remove your own administrator flag.")
        else:
            with transaction.atomic():
                User.objects.filter(pk=target.pk).update(full_name=d["full_name"], title=d["title"],
                                                         is_active=d["is_active"], is_staff=d["is_staff"])
                target.teams.set(d["teams"])
                if not d["is_active"]:
                    _end_sessions(target)
                audit("user.updated", target, f"User {target.email} updated", actor=request.user,
                      data={"is_active": d["is_active"], "is_staff": d["is_staff"]})
            messages.success(request, "User updated.")
            if not d["is_active"]:
                held = Assignment.objects.filter(kind="person", user=target).count()
                tasks = Task.objects.filter(assignee=target, status="open").count()
                if held or tasks:
                    messages.warning(request, f"{target} still holds {held} client(s) and {tasks} open task(s). "
                                     "They now appear in the attention queue so an administrator can hand them over.")
            return redirect("accounts:users")
    return render(request, "accounts/user_form.html", {"form": form, "reset": reset, "target": target, "title": f"Edit {target}"})


@require_POST
def user_reset_password(request, pk):
    _require_admin(request)
    target = get_object_or_404(User, pk=pk)
    form = ResetPasswordForm(request.POST, user=target)
    if form.is_valid():
        with transaction.atomic():
            target.set_password(form.cleaned_data["temporary_password"])
            target.must_change_password = True
            target.save(update_fields=["password", "must_change_password"])
            _end_sessions(target)
            audit("user.password_reset", target, f"Password reset for {target.email}", actor=request.user)
        messages.success(request, "Temporary password set; the user's existing sessions were ended.")
    else:
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
    return redirect("accounts:user_edit", pk=pk)


def _end_sessions(user):
    from django.contrib.sessions.models import Session

    for session in Session.objects.all().iterator():
        if session.get_decoded().get("_auth_user_id") == str(user.pk):
            session.delete()


@require_POST
def user_reset_two_factor(request, pk):
    """Administrator turns off two-step sign-in for someone who lost their phone."""
    _require_admin(request)
    target = get_object_or_404(User, pk=pk)
    services.disable_two_factor(target, actor=request.user)
    messages.success(request, f"Two-step sign-in turned off for {target}. They can set it up again after signing in.")
    return redirect("accounts:user_edit", pk=target.pk)


# --- Password reset by email (staff only) ---------------------------------------

class StyledPasswordResetForm(CrisGenMixin, PasswordResetForm):
    def get_users(self, email):
        # Only active accounts; Django's default also requires a usable password, which all ours have.
        return (u for u in super().get_users(email) if u.is_active)

    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
        context["workspace_name"] = get_policy()["workspace_name"]
        super().send_mail(subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name)
        user = context.get("user")
        if user is not None:
            audit("auth.password_reset_requested", user, "Password reset link emailed", actor=None)


class StyledSetPasswordForm(CrisGenMixin, SetPasswordForm):
    def save(self, commit=True):
        with transaction.atomic():
            user = super().save(commit=commit)
            User.objects.filter(pk=user.pk).update(must_change_password=False)
            audit("auth.password_reset", user, "Password reset with an emailed link", actor=user)
        services.record_success(user.email, "")
        return user


@method_decorator(login_not_required, name="dispatch")
class ResetRequestView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/email/password_reset.txt"
    subject_template_name = "accounts/email/password_reset_subject.txt"
    form_class = StyledPasswordResetForm
    success_url = reverse_lazy("accounts:password_reset_sent")

    def form_valid(self, form):
        # Light throttle per IP so the form cannot be used to flood inboxes. The answer looks the same either way.
        if not services.allow_reset_request(client_ip(self.request)):
            return redirect(self.success_url)
        return super().form_valid(form)


@method_decorator(login_not_required, name="dispatch")
class ResetSentView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_sent.html"


@method_decorator(login_not_required, name="dispatch")
class ResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    form_class = StyledSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")
    post_reset_login = False


@method_decorator(login_not_required, name="dispatch")
class ResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
