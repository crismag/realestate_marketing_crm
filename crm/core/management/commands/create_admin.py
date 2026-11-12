"""Create (or reset) a workspace administrator without any fixed password.

The password is read from CRM_ADMIN_PASSWORD, or prompted for, or generated and
printed once. The account must change its password at first sign-in.
"""
import getpass
import os
import secrets

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from crm.accounts.models import User
from crm.core.reference import ensure_reference_data
from crm.core.services import audit


class Command(BaseCommand):
    help = "Create a workspace administrator (no default password)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", default="Workspace Administrator")
        parser.add_argument("--generate", action="store_true", help="Generate a random temporary password and print it once")
        parser.add_argument("--reset", action="store_true", help="Reset the password if the user already exists")

    def handle(self, *args, **opts):
        email = opts["email"].strip().lower()
        existing = User.objects.filter(email=email).first()
        if existing and not opts["reset"]:
            raise CommandError(f"{email} already exists. Use --reset to set a new temporary password.")
        password = os.environ.get("CRM_ADMIN_PASSWORD", "")
        generated = False
        if not password:
            if opts["generate"] or not os.isatty(0):
                password, generated = secrets.token_urlsafe(18), True
            else:
                password = getpass.getpass("Temporary password: ")
                if password != getpass.getpass("Repeat: "):
                    raise CommandError("Passwords do not match.")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc
        ensure_reference_data()
        with transaction.atomic():
            if existing:
                existing.set_password(password)
                existing.is_staff = True
                existing.is_active = True
                existing.must_change_password = True
                existing.save()
                user, action = existing, "user.admin_reset"
            else:
                user = User.objects.create_user(email, opts["name"], password, is_staff=True, must_change_password=True)
                action = "user.admin_created"
            audit(action, user, f"Administrator {email} bootstrapped from the command line", actor=None, actor_kind="system")
        self.stdout.write(self.style.SUCCESS(f"Administrator {email} ready. They must change the password at first sign-in."))
        if generated:
            self.stdout.write(f"Temporary password (shown once): {password}")
