from django import forms
from django.contrib.auth import password_validation

from crm.core.forms import Form

from .models import Team, User


class LoginForm(Form):
    email = forms.EmailField(max_length=254, widget=forms.EmailInput(attrs={"autocomplete": "username", "autofocus": True}))
    password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class SecondFactorForm(Form):
    code = forms.CharField(max_length=20, label="Code", widget=forms.TextInput(attrs={
        "autocomplete": "one-time-code", "inputmode": "numeric", "autofocus": True}),
        help_text="The 6-digit code from your authenticator app, or one of your recovery codes.")


class PasswordConfirmForm(Form):
    password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
                               label="Your password")


class UserCreateForm(Form):
    email = forms.EmailField(max_length=254)
    full_name = forms.CharField(max_length=150)
    title = forms.CharField(max_length=100, required=False, help_text="Free text such as Agent or Marketing; not a permission.")
    teams = forms.ModelMultipleChoiceField(queryset=Team.objects.filter(active=True), required=False)
    is_staff = forms.BooleanField(required=False, label="Workspace administrator",
                                  help_text="Can manage user accounts and view backups. Does not change CRM access.")
    temporary_password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
                                         help_text="The user must change it at first sign-in.")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("temporary_password"):
            password_validation.validate_password(data["temporary_password"], User(email=data.get("email", ""),
                                                                                    full_name=data.get("full_name", "")))
        return data


class UserEditForm(Form):
    full_name = forms.CharField(max_length=150)
    title = forms.CharField(max_length=100, required=False)
    teams = forms.ModelMultipleChoiceField(queryset=Team.objects.filter(active=True), required=False)
    is_active = forms.BooleanField(required=False, label="Active (can sign in)")
    is_staff = forms.BooleanField(required=False, label="Workspace administrator")


class ResetPasswordForm(Form):
    temporary_password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_temporary_password(self):
        value = self.cleaned_data["temporary_password"]
        password_validation.validate_password(value, self.user)
        return value
