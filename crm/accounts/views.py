from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from crm.core.forms import CrisGenMixin
from crm.core.services import audit
from crm.work.models import Assignment, Task

from . import services
from .forms import LoginForm, ResetPasswordForm, UserCreateForm, UserEditForm
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
                services.record_success(email, ip)
                login(request, user)  # rotates the session key
                audit("auth.login", user, "Signed in", actor=user)
                if user.must_change_password:
                    messages.info(request, "Please choose a new password before continuing.")
                    return redirect("accounts:password_change")
                if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
                    return redirect(next_url)
                return redirect("core:today")
    return render(request, "accounts/login.html", {"form": form, "next": next_url})


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
