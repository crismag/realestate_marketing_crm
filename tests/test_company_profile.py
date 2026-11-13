"""Per-company setup: company profile, logo and first-run checklist (one install per company)."""
import io

import pytest

from crm.core.models import BrandLogo
from crm.core.services import get_policy, get_settings_row

pytestmark = pytest.mark.django_db

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _post(client, **extra):
    data = {"workspace_name": "Casa Realty", "legal_name": "Casa Realty Inc.", "phone": "+63 2 8123 4567",
            "email": "hello@casa.example.test", "website": "casa.example.test", "address": "1 Ayala Ave",
            "note": "", "version": get_settings_row().version, **extra}
    return client.post("/settings/company/", data)


def test_admin_saves_company_profile_and_logo(client, users):
    client.force_login(users["admin"])
    logo = io.BytesIO(PNG)
    logo.name = "logo.png"
    r = _post(client, logo=logo)
    assert r.status_code == 302
    policy = get_policy()
    assert policy["workspace_name"] == "Casa Realty"
    assert policy["company"]["website"] == "https://casa.example.test"
    assert BrandLogo.objects.get(pk=1).content_type == "image/png"
    page = client.get("/").content.decode()
    assert "Casa Realty" in page and "/brand/logo?v=" in page


def test_logo_is_public_with_safe_headers(client, users):
    client.force_login(users["admin"])
    logo = io.BytesIO(PNG)
    logo.name = "logo.png"
    _post(client, logo=logo)
    client.logout()
    r = client.get("/brand/logo")
    assert r.status_code == 200 and r["Content-Type"] == "image/png" and r["X-Content-Type-Options"] == "nosniff"
    assert client.get("/brand/logo", HTTP_IF_NONE_MATCH=r["ETag"]).status_code == 304


def test_svg_and_oversized_logos_are_refused(client, users):
    client.force_login(users["admin"])
    svg = io.BytesIO(b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>")
    svg.name = "logo.svg"
    r = _post(client, logo=svg)
    assert r.status_code == 200 and "PNG, JPEG or WebP" in r.content.decode()
    big = io.BytesIO(PNG + b"\x00" * 600_000)
    big.name = "big.png"
    assert "512 KB" in _post(client, logo=big).content.decode()
    assert not BrandLogo.objects.exists()


def test_non_admin_cannot_change_company_profile(client, users):
    client.force_login(users["ana"])
    assert client.get("/settings/company/").status_code == 200
    assert _post(client).status_code == 403


def test_company_details_fill_customer_email_placeholders(users, make_contact):
    from crm.comms.services import render_template, template_values
    from crm.core.services import update_policy

    policy = get_policy()
    policy["company"] = {**policy["company"], "phone": "+63 2 8123 4567"}
    update_policy(policy, actor=users["admin"], expected_version=get_settings_row().version)
    c = make_contact("Carla Customer")
    out = render_template("Call us on {{ company_phone }}", template_values(c, get_policy()))
    assert out == "Call us on +63 2 8123 4567"


def test_setup_checklist_shows_for_admin_until_done(client, users):
    client.force_login(users["admin"])
    page = client.get("/").content.decode()
    assert "Set up your CRM" in page
    client.force_login(users["ana"])
    assert "Set up your CRM" not in client.get("/").content.decode()


def test_sign_in_page_shows_company_name(client, users):
    client.force_login(users["admin"])
    _post(client)
    client.logout()
    assert "Sign in to Casa Realty" in client.get("/accounts/login/").content.decode()
