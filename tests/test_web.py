"""HTTP-level tests: the full journey through real views, page smoke checks, and security negatives."""
import datetime as dt
import re
from pathlib import Path

import pytest
from django.test import Client

from crm.automation.models import Notification
from crm.contacts.models import Contact, Interaction
from crm.core import clock
from crm.work.models import Assignment, Handover, Task

from .conftest import run_worker

PASSWORD = "a-long-test-password-1"
H = dt.timedelta(hours=1)
D = dt.timedelta(days=1)


def login(client, user):
    resp = client.post("/accounts/login/", {"email": user.email, "password": PASSWORD})
    assert resp.status_code == 302, resp.content[:500]
    return client


def local_input(value):
    """Format a UTC datetime the way <input type=datetime-local> sends it in the workspace timezone."""
    from zoneinfo import ZoneInfo

    return value.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%dT%H:%M")


@pytest.mark.django_db
def test_full_journey_through_the_web(users, pool, now):
    ana, ben, cora = users["ana"], users["ben"], users["cora"]
    start = now - 3 * D
    a, b, c = Client(), Client(), Client()

    with clock.frozen(start):
        # 1. Coordinator captures a walk-in into the shared pool.
        login(c, cora)
        resp = c.post("/contacts/new/", {"display_name": "Journey Jo", "email": "jo@example.test", "phone": "",
                                         "destination": "pool", "pool": pool.pk,
                                         "inquiry_message": "Looking for a 2-bedroom near the park",
                                         "inquiry_channel": "in_person"})
        assert resp.status_code == 302
        contact = Contact.objects.get(display_name="Journey Jo")
        assert contact.assignment.kind == "pool"

        # 2. Ana sees it in shared work and claims it.
        login(a, ana)
        assert "Journey Jo" in a.get("/work/shared/").content.decode()
        resp = a.post(f"/work/claim/{contact.pk}/", {"version": contact.assignment.version, "operation_id": "op-1"})
        assert resp.status_code == 302
        contact.assignment.refresh_from_db()
        assert contact.assignment.user == ana

    with clock.frozen(start + 2 * H):
        # 3. Ana records the tour and links it to the inquiry.
        inquiry = contact.inquiries.get()
        resp = a.post(f"/contacts/{contact.pk}/interactions/", {
            "ix-kind": "meeting_tour", "ix-channel": "in_person", "ix-summary": "Toured unit 4B; liked the light.",
            "ix-occurred_at": local_input(start + H), "ix-inquiry": inquiry.pk})
        assert resp.status_code == 302, resp.content.decode()[:2000]
        assert Interaction.objects.filter(contact=contact, kind="meeting_tour").count() == 1
        inquiry.refresh_from_db()
        assert inquiry.status == "responded"

        # 4. Ana creates the next action, due tomorrow.
        due = start + D
        resp = a.post(f"/work/tasks/new/{contact.pk}/", {"task-title": "Send floor plans", "task-kind": "follow_up",
                                                         "task-assignee": ana.pk, "task-due_at": local_input(due)})
        assert resp.status_code == 302, resp.content.decode()[:2000]
        task = Task.objects.get(contact=contact, title="Send floor plans")
        a.get("/")  # consume flash messages that mention the name
        page = a.get("/attention/?scope=mine").content.decode()
        assert "Journey Jo" not in page  # covered by a future next action

    with clock.frozen(start + 2 * D):
        # 5. Attention becomes due: the task is overdue.
        page = a.get("/attention/?scope=mine").content.decode()
        assert "Journey Jo" in page and "Task overdue" in page

        # 6. The worker sweep sends Ana a reminder notification (once, even if run twice).
        run_worker()
        run_worker()
        reminders = Notification.objects.filter(recipient=ana, task=task)
        assert reminders.count() == 1
        assert "Send floor plans" in a.get("/automation/notifications/").content.decode()

        # 7. Ana requests a handover to Ben, moving the task on acceptance. She stays responsible meanwhile.
        resp = a.post(f"/work/handover/new/{contact.pk}/", {
            "kind": "transfer", "recipient": ben.pk, "reason": "Ben covers the park district",
            "context": "Wants 2BR; toured 4B", "version": contact.assignment.version, f"task_{task.pk}": "transfer"})
        assert resp.status_code == 302, resp.content.decode()[:3000]
        handover = Handover.objects.get(contact=contact)
        assert Assignment.objects.get(contact=contact).user == ana

        # Nobody but the recipient may accept.
        resp = a.post(f"/work/handover/{handover.pk}/accept/")
        handover.refresh_from_db()
        assert handover.state == "requested"

        # 8. Ben accepts.
        login(b, ben)
        assert "Journey Jo" in b.get("/work/shared/").content.decode()
        resp = b.post(f"/work/handover/{handover.pk}/accept/")
        assert resp.status_code == 302
        handover.refresh_from_db()
        task.refresh_from_db()
        assert handover.state == "accepted"
        assert Assignment.objects.get(contact=contact).user == ben
        assert task.assignee == ben

        # 9. Reporting reflects the source facts and drills down to them.
        q = f"from={(start - D).date()}&to={(start + 3 * D).date()}"
        report = b.get(f"/reports/?{q}").content.decode()
        assert "Ben Broker" in report
        drill = b.get(f"/reports/drill/?metric=acquisitions&source=none&{q}").content.decode()
        assert "Journey Jo" in drill
        drill = b.get(f"/reports/drill/?metric=responded&{q}").content.decode()
        assert "Journey Jo" in drill

        # The profile timeline tells the whole story.
        profile = b.get(f"/contacts/{contact.pk}/").content.decode()
        for fact in ("Toured unit 4B", "Send floor plans", "Ben covers the park district"):
            assert fact in profile


PAGES = ["/", "/contacts/", "/contacts/new/", "/contacts/opportunities/", "/work/shared/", "/work/tasks/",
         "/attention/", "/attention/?scope=all", "/automation/rules/", "/automation/jobs/",
         "/automation/notifications/", "/messages/", "/reports/", "/reports/spend/", "/settings/",
         "/settings/audit/", "/settings/pools/new/", "/settings/teams/new/", "/settings/sources/new/",
         "/accounts/users/", "/accounts/users/new/", "/accounts/password/"]


@pytest.mark.django_db
def test_every_page_renders_for_admin_with_data(client, users, pool, make_contact, frozen):
    c = make_contact("Smoke Sam", email="sam@example.test", inquiry="Hello")
    make_contact("Pool Pat", destination="pool", pool=pool)
    from crm.work import services as work

    work.create_task(c, actor=users["ana"], assignee=users["ana"], title="Call back", kind="call", due_at=frozen - H)
    run_worker()
    login(client, users["admin"])
    pages = PAGES + [f"/contacts/{c.pk}/", f"/contacts/{c.pk}/edit/",
                     f"/settings/pools/{pool.pk}/", f"/accounts/users/{users['ana'].pk}/"]
    from crm.automation.models import Job, Rule
    from crm.comms.models import MessageTemplate

    pages += [f"/automation/rules/{r.key}/" for r in Rule.objects.all()]
    pages += [f"/automation/jobs/{j.pk}/" for j in Job.objects.all()[:5]]
    pages += [f"/messages/templates/{t.pk}/" for t in MessageTemplate.objects.all()]
    for url in pages:
        resp = client.get(url)
        assert resp.status_code == 200, f"{url} -> {resp.status_code}"
    # Handler-only page, as the handler.
    ana = Client()
    login(ana, users["ana"])
    assert ana.get(f"/work/handover/new/{c.pk}/").status_code == 200


@pytest.mark.django_db
def test_anonymous_users_are_sent_to_login(client):
    for url in PAGES:
        resp = client.get(url)
        assert resp.status_code == 302 and resp["Location"].startswith("/accounts/login/"), url
    assert client.get("/healthz").status_code == 200


@pytest.mark.django_db
def test_csrf_is_enforced(users, make_contact):
    c = make_contact("Csrf Cas")
    client = Client(enforce_csrf_checks=True)
    client.force_login(users["ana"])
    resp = client.post(f"/contacts/{c.pk}/interactions/", {"ix-kind": "note", "ix-channel": "other", "ix-summary": "x"})
    assert resp.status_code == 403
    assert not Interaction.objects.filter(contact=c).exists()
    # Login form is CSRF-protected as well.
    resp = Client(enforce_csrf_checks=True).post("/accounts/login/", {"email": "ana@example.test", "password": PASSWORD})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_login_throttling_locks_after_repeated_failures(client, users):
    for _ in range(5):
        resp = client.post("/accounts/login/", {"email": "ana@example.test", "password": "wrong-password-x"})
        assert resp.status_code == 200
    # Even the right password is refused while locked.
    resp = client.post("/accounts/login/", {"email": "ana@example.test", "password": PASSWORD})
    assert resp.status_code == 200
    assert "Too many failed sign-in attempts" in resp.content.decode()


@pytest.mark.django_db
def test_logout_requires_post_and_ends_session(client, users):
    login(client, users["ana"])
    assert client.get("/accounts/logout/").status_code == 405
    client.post("/accounts/logout/")
    assert client.get("/").status_code == 302


@pytest.mark.django_db
def test_open_redirect_is_refused(client, users):
    resp = client.post("/accounts/login/?next=https://evil.example/", {"email": users["ana"].email, "password": PASSWORD,
                                                                      "next": "https://evil.example/"})
    assert resp.status_code == 302 and resp["Location"] == "/"


@pytest.mark.django_db
def test_must_change_password_blocks_other_pages(client, users):
    ana = users["ana"]
    ana.must_change_password = True
    ana.save()
    login(client, ana)
    resp = client.get("/contacts/")
    assert resp.status_code == 302 and resp["Location"].startswith("/accounts/password/")


@pytest.mark.django_db
def test_non_admin_cannot_manage_users_or_settings(client, users):
    login(client, users["ana"])
    assert client.get("/accounts/users/new/").status_code == 403
    assert client.get(f"/accounts/users/{users['ben'].pk}/").status_code == 403
    resp = client.post("/accounts/users/new/", {"email": "x@example.test", "full_name": "X", "temporary_password": "p" * 20})
    assert resp.status_code == 403
    assert client.post("/settings/", {"workspace_name": "Hacked"}).status_code == 403
    assert client.post("/settings/pools/new/", {"name": "Hacked pool"}).status_code == 403


@pytest.mark.django_db
def test_mass_assignment_cannot_change_responsibility_via_edit(client, users, make_contact):
    c = make_contact("Mass Assign")
    login(client, users["ben"])
    client.post(f"/contacts/{c.pk}/edit/", {"display_name": "Renamed", "version": c.version, "assignment": users["ben"].pk,
                                            "lifecycle": "client", "archived_at": "2026-01-01"})
    c.refresh_from_db()
    assert c.assignment.user == users["ana"]
    assert c.lifecycle == "lead" and c.archived_at is None


@pytest.mark.django_db
def test_user_content_is_escaped(client, users, make_contact):
    c = make_contact("<script>alert(1)</script>")
    login(client, users["ana"])
    for url in (f"/contacts/{c.pk}/", "/contacts/", "/attention/?scope=all"):
        body = client.get(url).content.decode()
        assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in client.get(f"/contacts/{c.pk}/").content.decode()


@pytest.mark.django_db
def test_search_input_is_not_sql(client, users, make_contact):
    make_contact("Robert Tables")
    login(client, users["ana"])
    resp = client.get("/contacts/", {"q": "x' OR '1'='1"})
    assert resp.status_code == 200 and "Robert Tables" not in resp.content.decode()


@pytest.mark.django_db
def test_csv_export_neutralises_formulas(client, users, make_contact):
    make_contact("=HYPERLINK(\"http://evil\")", phone="+1 555 0100")
    login(client, users["ana"])
    resp = client.get("/contacts/", {"format": "csv"})
    assert resp.status_code == 200 and resp["Content-Type"].startswith("text/csv")
    body = resp.content.decode()
    assert "'=HYPERLINK" in body
    assert "\n=HYPERLINK" not in body and ",=HYPERLINK" not in body


@pytest.mark.django_db
def test_security_headers_and_cookie_flags(client, users):
    resp = client.get("/accounts/login/")
    assert "script-src 'self'" in resp["Content-Security-Policy"]
    assert resp["X-Frame-Options"] == "DENY"
    assert resp["X-Content-Type-Options"] == "nosniff"
    assert resp["Referrer-Policy"]
    resp = client.post("/accounts/login/", {"email": users["ana"].email, "password": PASSWORD})
    cookie = resp.cookies["crm_session"] if "crm_session" in resp.cookies else resp.cookies["sessionid"]
    assert cookie["httponly"] and cookie["samesite"] == "Lax"


@pytest.mark.django_db
def test_stale_edit_is_rejected_not_overwritten(client, users, make_contact):
    c = make_contact("Version Vic")
    login(client, users["ana"])
    old = c.version
    client.post(f"/contacts/{c.pk}/edit/", {"display_name": "First edit", "version": old})
    resp = client.post(f"/contacts/{c.pk}/edit/", {"display_name": "Stale edit", "version": old})
    c.refresh_from_db()
    assert c.display_name == "First edit"
    assert resp.status_code in (200, 409)


def test_templates_have_no_inline_styles_or_scripts():
    """The Content-Security-Policy blocks inline style/script, so templates must not rely on them."""
    root = Path(__file__).resolve().parent.parent / "templates"
    offenders = []
    for path in root.rglob("*.html"):
        text = path.read_text()
        if re.search(r"\sstyle=|<script(?![^>]*\bsrc=)|\son[a-z]+=", text):
            offenders.append(str(path.relative_to(root)))
    assert offenders == []
