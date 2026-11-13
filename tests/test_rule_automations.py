"""Rule-based automations C-R2 (stalled opportunity), C-R3 (follow-up suggestion), C-R6 (duplicate matching).

All three are implementation defaults (docs/IMPLEMENTATION_DEFAULTS.md); none creates, merges or
reassigns anything on its own.
"""
import datetime as dt

import pytest

from crm.attention import services as attention
from crm.contacts import services as contacts
from crm.contacts.models import Contact
from crm.core import clock
from crm.core.models import AuditEvent
from crm.core.services import get_policy, get_settings_row, update_policy
from crm.work.models import Task

pytestmark = pytest.mark.django_db
H = dt.timedelta(hours=1)
D = dt.timedelta(days=1)


def reasons(contact, policy, now):
    items = attention.evaluate(now=now, policy=policy, contact_ids=[contact.pk])
    return {r.code: r for r in items[0].active_reasons} if items else {}


def make_opp(contact, actor, **data):
    return contacts.save_opportunity(contact, actor=actor, opportunity=None, expected_version=None,
                                     data={"title": "Unit 4B", "stage": "new", **data})


# --- C-R2 stalled opportunity -------------------------------------------------------------

def test_stage_unchanged_past_limit_is_flagged_with_reason(users, make_contact, policy, now):
    with clock.frozen(now - 30 * D):
        c = make_contact("Stella Stalled")
        make_opp(c, users["ana"])
    r = reasons(c, policy, now)
    assert "opportunity_stalled" in r
    assert "stage unchanged" in r["opportunity_stalled"].detail and "21 days" in r["opportunity_stalled"].detail
    assert "opportunity_stalled" not in reasons(c, policy, now - 10 * D)


def test_editing_other_fields_does_not_reset_the_stall_clock(users, make_contact, policy, now):
    with clock.frozen(now - 30 * D):
        c = make_contact("Edith Edits")
        opp = make_opp(c, users["ana"])
    with clock.frozen(now - D):
        opp = contacts.save_opportunity(c, actor=users["ana"], opportunity=opp, expected_version=opp.version,
                                        data={"title": "Unit 4B (corner)", "stage": "new", "amount_minor": 100})
    assert "opportunity_stalled" in reasons(c, policy, now)
    with clock.frozen(now - D):
        contacts.save_opportunity(c, actor=users["ana"], opportunity=opp, expected_version=opp.version,
                                  data={"title": opp.title, "stage": "viewing"})
    assert "opportunity_stalled" not in reasons(c, policy, now)
    assert AuditEvent.objects.filter(action="opportunity.stage_changed").count() == 1


def test_past_expected_close_is_flagged_and_closed_opportunities_are_not(users, make_contact, policy, now):
    with clock.frozen(now - 2 * D):
        c = make_contact("Clara Close")
        opp = make_opp(c, users["ana"], expected_close=(now - D).date())
    assert "expected close" in reasons(c, policy, now)["opportunity_stalled"].detail
    contacts.close_opportunity(opp, actor=users["ana"], outcome="lost", reason="Bought elsewhere",
                               expected_version=opp.version, policy=policy)
    assert "opportunity_stalled" not in reasons(c, policy, now)


def test_stall_checks_can_be_switched_off(users, make_contact, policy, now):
    with clock.frozen(now - 30 * D):
        c = make_contact("Otto Off")
        make_opp(c, users["ana"], expected_close=(now - D).date())
    policy["attention"]["stalled_opportunity_days"] = 0
    policy["attention"]["flag_past_expected_close"] = False
    assert "opportunity_stalled" not in reasons(c, policy, now)


def test_stalled_reason_is_snoozable_and_keeps_ownership(users, make_contact, policy, now):
    with clock.frozen(now - 30 * D):
        c = make_contact("Sam Snooze")
        make_opp(c, users["ana"])
    with clock.frozen(now):
        attention.snooze(c, actor=users["ana"], reason_code="opportunity_stalled", until=now + 3 * D, note="Buyer travelling")
    assert "opportunity_stalled" not in reasons(c, policy, now)
    assert Contact.objects.get(pk=c.pk).assignment.user == users["ana"]


# --- C-R3 follow-up suggestion ------------------------------------------------------------

def log(client, contact, kind="meeting_tour"):
    return client.post(f"/contacts/{contact.pk}/interactions/", {
        "ix-kind": kind, "ix-channel": "in_person", "ix-summary": "Viewed unit 4B", "ix-occurred_at": ""})


def test_tour_prefills_follow_up_but_creates_nothing(client, users, make_contact, frozen):
    c = make_contact("Tara Tour")
    client.force_login(users["ana"])
    resp = log(client, c)
    assert resp.status_code == 302 and "?suggest=" in resp["Location"]
    page = client.get(resp["Location"]).content.decode()
    assert "Suggested next action" in page and "Follow up after the tour" in page
    assert 'value="Follow up after the tour"' in page
    assert Task.objects.filter(contact=c).count() == 0


def test_no_suggestion_when_a_future_task_exists_or_disabled(client, users, make_contact, frozen):
    from crm.work import services as work

    c = make_contact("Fiona Future")
    work.create_task(c, actor=users["ana"], assignee=users["ana"], title="Call back", kind="follow_up",
                     due_at=frozen + 2 * D, description="", critical=False)
    client.force_login(users["ana"])
    page = client.get(log(client, c)["Location"]).content.decode()
    assert "Suggested next action" not in page

    d = make_contact("Dora Disabled")
    policy = get_policy()
    policy["followup_suggestions"]["enabled"] = False
    update_policy(policy, actor=users["admin"], expected_version=get_settings_row().version, note="test")
    page = client.get(log(client, d)["Location"]).content.decode()
    assert "Suggested next action" not in page


def test_suggestion_only_for_own_recent_interaction(client, users, make_contact, frozen):
    c = make_contact("Owen Other")
    client.force_login(users["ana"])
    location = log(client, c)["Location"]
    client.force_login(users["ben"])
    assert "Suggested next action" not in client.get(location).content.decode()
    client.force_login(users["ana"])
    with clock.frozen(frozen + 2 * H):
        assert "Suggested next action" not in client.get(location).content.decode()


def test_notes_get_no_suggestion(client, users, make_contact, frozen):
    c = make_contact("Nina Note")
    client.force_login(users["ana"])
    assert "Suggested next action" not in client.get(log(client, c, kind="note")["Location"]).content.decode()


# --- C-R6 duplicate matching --------------------------------------------------------------

def test_name_in_other_order_with_accents_is_a_candidate(make_contact):
    existing = make_contact("José Ramírez")
    found = list(contacts.duplicate_candidates(name="Ramirez, Jose"))
    assert found == [existing]
    assert contacts.match_reasons(existing, name="Ramirez, Jose") == ["same name, different order or spelling marks"]


def test_single_first_name_does_not_flag_everyone(make_contact):
    make_contact("Maria Santos")
    assert list(contacts.duplicate_candidates(name="Maria")) == []


def test_plus_tag_email_is_a_candidate_both_ways(make_contact):
    tagged = make_contact("Tag One", email="jane+web@example.test")
    plain = make_contact("Tag Two", email="jane@example.test")
    assert set(contacts.duplicate_candidates(email="jane@example.test", exclude_id=plain.pk)) == {tagged}
    assert set(contacts.duplicate_candidates(email="JANE+promo@example.test")) == {tagged, plain}
    assert contacts.match_reasons(tagged, email="jane@example.test") == ["same email apart from a +tag"]
    assert list(contacts.duplicate_candidates(email="janet@example.test")) == []


def test_renaming_updates_the_match_key(users, make_contact):
    c = make_contact("Old Name")
    contacts.update_contact(c, actor=users["ana"], data={"display_name": "Lena Lopez"}, expected_version=c.version)
    assert list(contacts.duplicate_candidates(name="lopez lena")) == [Contact.objects.get(pk=c.pk)]


def test_capture_screen_explains_match_and_still_never_merges(client, users, make_contact):
    existing = make_contact("Carla Cruz")
    client.force_login(users["ana"])
    resp = client.post("/contacts/new/", {"display_name": "Cruz Carla", "destination": "me"})
    page = resp.content.decode()
    assert resp.status_code == 200 and f"/contacts/{existing.pk}/" in page
    assert "Matched on same name, different order or spelling marks" in page
    assert Contact.objects.count() == 1


# --- review follow-ups ---------------------------------------------------------------------

def test_two_stalled_opportunities_share_one_reason_and_one_snooze(users, make_contact, policy, now):
    with clock.frozen(now - 30 * D):
        c = make_contact("Two Deals")
        make_opp(c, users["ana"], title="Unit 4B")
        make_opp(c, users["ana"], title="Unit 9C")
    items = attention.evaluate(now=now, policy=policy, contact_ids=[c.pk])
    stalled = [r for r in items[0].active_reasons if r.code == "opportunity_stalled"]
    assert len(stalled) == 1 and "Unit 4B" in stalled[0].detail and "Unit 9C" in stalled[0].detail


def test_stage_change_shows_in_profile_history(client, users, make_contact):
    c = make_contact("History Hal")
    opp = make_opp(c, users["ana"])
    contacts.save_opportunity(c, actor=users["ana"], opportunity=opp, expected_version=opp.version,
                              data={"title": opp.title, "stage": "viewing"})
    client.force_login(users["ana"])
    assert "stage new -&gt; viewing" in client.get(f"/contacts/{c.pk}/").content.decode()


def test_oversized_suggest_parameter_is_ignored(client, users, make_contact):
    c = make_contact("Big Number")
    client.force_login(users["ana"])
    for value in ("9" * 19, "9" * 40):
        resp = client.get(f"/contacts/{c.pk}/?suggest={value}")
        assert resp.status_code == 200 and "Suggested next action" not in resp.content.decode()


def test_non_latin_names_match_in_any_order(make_contact):
    existing = make_contact("王 小明")
    assert list(contacts.duplicate_candidates(name="小明 王")) == [existing]


def test_overlong_name_gets_no_key_rather_than_a_truncated_one():
    from crm.contacts.models import name_key

    assert name_key("a" * 300 + " b") == ""
    assert name_key("Smith, John") == "john smith"
