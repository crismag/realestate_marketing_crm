"""Password reset by email and two-step sign-in (product step 3)."""
import re

import pytest
from django.core import mail

from crm.accounts import services, totp
from crm.accounts.models import User
from crm.core import clock

pytestmark = pytest.mark.django_db
PW = "a-long-test-password-1"


@pytest.fixture(autouse=True)
def locmem_mail(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


def _code(user, offset=0):
    return totp.code_at(user.totp_secret, int(clock.now().timestamp() // 30) + offset)


def _enable(user):
    secret = totp.new_secret()
    codes = services.enable_two_factor(user, secret=secret, code=totp.code_at(secret, int(clock.now().timestamp() // 30)))
    user.refresh_from_db()
    return codes


def test_reset_link_emails_and_sets_new_password(client, users):
    r = client.post("/accounts/password-reset/", {"email": "ana@example.test"})
    assert r.status_code == 302 and len(mail.outbox) == 1
    link = re.search(r"https?://[^\s]+/password-reset/[^\s]+/", mail.outbox[0].body).group(0)
    path = link.split("testserver", 1)[1]
    r = client.get(path, follow=True)
    form_path = r.redirect_chain[-1][0]
    r = client.post(form_path, {"new_password1": "Brand-new-passphrase-42", "new_password2": "Brand-new-passphrase-42"})
    assert r.status_code == 302
    assert User.objects.get(email="ana@example.test").check_password("Brand-new-passphrase-42")
    # The link is single use.
    assert b"expired or was already used" in client.get(path, follow=True).content


def test_reset_does_not_reveal_unknown_or_inactive_accounts(client, users):
    users["ben"].is_active = False
    users["ben"].save()
    for email in ("nobody@example.test", "ben@example.test"):
        assert client.post("/accounts/password-reset/", {"email": email}).status_code == 302
    assert mail.outbox == []


def test_reset_requests_are_throttled_per_ip(client, users):
    for _ in range(8):
        client.post("/accounts/password-reset/", {"email": "ana@example.test"})
    assert len(mail.outbox) == 5


def test_two_step_sign_in_requires_code(client, users):
    _enable(users["ana"])
    r = client.post("/accounts/login/", {"email": "ana@example.test", "password": PW})
    assert r["Location"] == "/accounts/login/verify/"
    assert client.get("/").status_code == 302  # not signed in yet
    assert b"not right" in client.post("/accounts/login/verify/", {"code": "000000"}).content
    users["ana"].refresh_from_db()
    r = client.post("/accounts/login/verify/", {"code": _code(users["ana"], 1)})  # setup used the current step
    assert r.status_code == 302 and client.get("/").status_code == 200


def test_code_cannot_be_replayed(users):
    _enable(users["ana"])
    user = User.objects.get(pk=users["ana"].pk)
    code = _code(user, 1)
    assert services.verify_second_factor(user, code)
    user.refresh_from_db()
    assert not services.verify_second_factor(user, code)


def test_recovery_code_works_once(users):
    codes = _enable(users["ana"])
    user = User.objects.get(pk=users["ana"].pk)
    assert services.verify_second_factor(user, codes[0].upper())
    user.refresh_from_db()
    assert not services.verify_second_factor(user, codes[0])
    assert len(user.recovery_code_hashes) == 7


def test_setup_page_turns_on_with_valid_code(client, users):
    client.force_login(users["ana"])
    page = client.get("/accounts/two-step/").content.decode()
    assert "<svg" in page
    secret = client.session["two_factor_setup_secret"]
    r = client.post("/accounts/two-step/", {"code": totp.code_at(secret, int(clock.now().timestamp() // 30))})
    assert "Save your recovery codes" in r.content.decode()
    assert User.objects.get(pk=users["ana"].pk).two_factor_enabled


def test_company_can_require_two_step(client, users):
    from crm.core.services import get_policy, get_settings_row, update_policy

    policy = get_policy()
    policy["security"] = {"require_two_factor": True}
    update_policy(policy, actor=users["admin"], expected_version=get_settings_row().version)
    client.force_login(users["ana"])
    assert client.get("/contacts/")["Location"] == "/accounts/two-step/"
    assert client.get("/accounts/two-step/").status_code == 200


def test_admin_can_reset_lost_phone(client, users):
    _enable(users["ana"])
    client.force_login(users["admin"])
    client.post(f"/accounts/users/{users['ana'].pk}/reset-two-step/")
    assert not User.objects.get(pk=users["ana"].pk).two_factor_enabled
    client.force_login(users["ben"])
    assert client.post(f"/accounts/users/{users['ana'].pk}/reset-two-step/").status_code == 403
