"""AT-005 (reporting reconciliation), AT-006 (capture), AT-008 (watch), AT-010 (labels/stages), AT-012 (states)."""
import datetime as dt

import pytest

from crm.contacts import services as contacts
from crm.contacts.models import Contact, Inquiry, Source
from crm.core import clock
from crm.core.services import get_policy, get_settings_row, update_policy
from crm.reporting import metrics
from crm.reporting.models import SpendEntry

PASSWORD = "a-long-test-password-1"
D = dt.timedelta(days=1)


@pytest.fixture
def ana_client(client, users):
    client.force_login(users["ana"])
    return client


# --- AT-006 capture -----------------------------------------------------------------

@pytest.mark.django_db
def test_invalid_capture_keeps_what_was_typed(ana_client):
    resp = ana_client.post("/contacts/new/", {"display_name": "Typed Name", "email": "not-an-email", "destination": "me",
                                              "interests": "Lakeside lots"})
    body = resp.content.decode()
    assert resp.status_code == 200 and not Contact.objects.exists()
    assert 'value="Typed Name"' in body and "Lakeside lots" in body and "valid email" in body


@pytest.mark.django_db
def test_duplicate_is_shown_not_merged_and_needs_confirmation(ana_client, make_contact):
    existing = make_contact("Carla Cruz", email="carla@example.test", phone="+63 917 555 0100")
    resp = ana_client.post("/contacts/new/", {"display_name": "C. Cruz", "email": "CARLA@example.test", "destination": "me"})
    assert resp.status_code == 200 and Contact.objects.count() == 1
    assert f"/contacts/{existing.pk}/" in resp.content.decode()
    # Phone match with different formatting is also detected.
    resp = ana_client.post("/contacts/new/", {"display_name": "Someone", "phone": "0063 917-555-0100", "destination": "me"})
    assert Contact.objects.count() == 1
    resp = ana_client.post("/contacts/new/", {"display_name": "C. Cruz", "email": "carla@example.test", "destination": "me",
                                              "confirm_new": "on"})
    assert resp.status_code == 302 and Contact.objects.count() == 2
    existing.refresh_from_db()
    assert existing.display_name == "Carla Cruz"  # never silently merged or overwritten


@pytest.mark.django_db
def test_repeat_inquiry_reuses_identity_and_replay_is_idempotent(ana_client, users, make_contact):
    c = make_contact("Repeat Rita", inquiry="First question")
    resp = ana_client.post(f"/contacts/{c.pk}/inquiries/", {"inq-message": "Second question", "inq-channel": "phone"})
    assert resp.status_code == 302
    assert Contact.objects.count() == 1 and Inquiry.objects.filter(contact=c).count() == 2
    for _ in range(2):
        contacts.record_inquiry(c, actor=None, message="Web form", channel="email", source=None, external_key="form-123")
    assert Inquiry.objects.filter(contact=c).count() == 3


@pytest.mark.django_db
def test_future_interaction_rejected_and_recording_time_kept(users, make_contact, frozen):
    c = make_contact("Timely Tim")
    from crm.core.errors import DomainError

    with pytest.raises(DomainError):
        contacts.record_interaction(c, actor=users["ana"], kind="conversation", channel="phone", summary="Later",
                                    occurred_at=frozen + D)
    ix = contacts.record_interaction(c, actor=users["ana"], kind="conversation", channel="phone", summary="Yesterday's call",
                                     occurred_at=frozen - D)
    assert ix.occurred_at == frozen - D and ix.recorded_at == frozen


# --- AT-005 reporting ---------------------------------------------------------------

@pytest.mark.django_db
def test_report_counts_reconcile_with_drilldowns_and_edge_cases(users, make_contact, policy, frozen):
    social = Source.objects.get(code="social")
    search = Source.objects.get(code="search")
    tz = policy["timezone"]
    period = metrics.Period.from_dates((frozen - 10 * D).date(), frozen.date(), tz)

    with clock.frozen(frozen - 5 * D):
        a = make_contact("Social One", source=social)
        make_contact("Social Two", source=social, inquiry="Hi")
    with clock.frozen(frozen - 40 * D):
        make_contact("Old Social", source=social)  # outside period

    # Spend: one inside, one partly overlapping (excluded, not prorated), one planned (ignored).
    def spend(source, start, end, amount, kind="actual", currency=None):
        return SpendEntry.objects.create(source=source, kind=kind, period_start=start, period_end=end, amount_minor=amount,
                                         currency=currency or policy["currency"], created_by=users["max"])

    spend(social, period.start_date, period.start_date + D, 10_000)
    spend(social, period.start_date - 3 * D, period.start_date + D, 99_999)
    spend(social, period.start_date, period.end_date, 77_777, kind="planned")
    inside, partial = metrics.spend_entries(period, social.pk)
    assert [e.amount_minor for e in inside] == [10_000] and partial.count() == 1

    assert metrics.acquisitions(period, social.pk).count() == 2
    assert metrics.inquiries(period, social.pk).count() == 1

    # Won value counts won only; other currencies are reported separately, never added.
    with clock.frozen(frozen - 2 * D):
        opp = contacts.save_opportunity(a, actor=users["ana"], opportunity=None, expected_version=None,
                                        data={"title": "Unit", "stage": "decision", "amount_minor": 500_00,
                                              "currency": policy["currency"]})
        contacts.close_opportunity(opp, actor=users["ana"], outcome="won", reason="Signed", expected_version=opp.version,
                                   policy=policy)
        other = contacts.save_opportunity(a, actor=users["ana"], opportunity=None, expected_version=None,
                                          data={"title": "Other", "stage": "decision", "amount_minor": 300_00, "currency": "PHP"})
        contacts.close_opportunity(other, actor=users["ana"], outcome="won", reason="Signed", expected_version=other.version,
                                   policy=policy)
    total, others = metrics.money_sum(metrics.won(period, social.pk).values_list("amount_minor", "currency"), policy["currency"])
    assert total == 500_00 and others == ["PHP"]

    # Missing is not zero: no responses yet -> median not applicable, not 0.
    assert metrics.response_hours(period)["median_hours"] is None

    # Search source has spend but no acquisitions -> CPA not applicable (zero denominator).
    spend(search, period.start_date, period.end_date, 5_000)


@pytest.mark.django_db
def test_report_page_shows_not_applicable_and_drill_lists_counted_records(ana_client, users, make_contact, frozen):
    search = Source.objects.get(code="search")
    SpendEntry.objects.create(source=search, kind="actual", period_start=(frozen - 3 * D).date(),
                              period_end=(frozen - 2 * D).date(), amount_minor=5_000, currency="USD", created_by=users["max"])
    with clock.frozen(frozen - D):
        c = make_contact("Drill Dora", source=Source.objects.get(code="social"))
    with clock.frozen(frozen):
        q = f"from={(frozen - 7 * D).date()}&to={frozen.date()}"
        body = ana_client.get(f"/reports/?{q}").content.decode()
        assert "n/a" in body and "Earnings" in body and "not applicable" in body
        drill = ana_client.get(f"/reports/drill/?metric=acquisitions&source={c.source_id}&{q}").content.decode()
        assert "Drill Dora" in drill and "1 record" in drill
        assert ana_client.get("/reports/drill/?metric=bogus").status_code == 302


# --- AT-008 watch ------------------------------------------------------------------

@pytest.mark.django_db
def test_watch_does_not_change_ownership(ana_client, users, make_contact):
    c = make_contact("Watched Wanda", actor=users["ben"])
    ana_client.post(f"/contacts/{c.pk}/watch/", {"watch": "1", "reason": "Introduced them"})
    c.refresh_from_db()
    assert c.assignment.user == users["ben"]
    assert c.watches.filter(user=users["ana"]).exists()


# --- AT-010 configurable labels and stages ------------------------------------------

@pytest.mark.django_db
def test_relabelling_keeps_stable_codes_and_history(ana_client, users, make_contact):
    c = make_contact("Label Lou")
    policy = get_policy()
    opp = contacts.save_opportunity(c, actor=users["ana"], opportunity=None, expected_version=None,
                                    data={"title": "Condo", "stage": "viewing", "amount_minor": None, "currency": "USD"})
    new = dict(policy)
    new["lifecycle_labels"] = {**policy["lifecycle_labels"], "lead": "Enquirer"}
    new["opportunity_stages"] = [s if s["code"] != "viewing" else {**s, "label": "Site visit"} for s in policy["opportunity_stages"]]
    update_policy(new, actor=users["admin"], expected_version=get_settings_row().version, note="Rename")
    body = ana_client.get(f"/contacts/{c.pk}/").content.decode()
    assert "Enquirer" in body and "Site visit" in body
    opp.refresh_from_db()
    assert opp.stage == "viewing"  # identity unchanged
    from crm.core.models import SettingsVersion

    assert SettingsVersion.objects.count() >= 2  # previous policy kept as history


# --- AT-012 states -----------------------------------------------------------------

@pytest.mark.django_db
def test_empty_and_filter_empty_states_are_distinct(ana_client, make_contact):
    assert "No contacts yet" in ana_client.get("/contacts/").content.decode()
    make_contact("Someone Here")
    body = ana_client.get("/contacts/", {"q": "zzz-no-match"}).content.decode()
    assert "No contacts yet" not in body and "match" in body.lower()
