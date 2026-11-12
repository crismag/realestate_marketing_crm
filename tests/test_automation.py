"""AT-004 / AT-008 / AT-009 / AT-011: durable worker, idempotency, routing, stop policies."""
import datetime as dt

import pytest

from crm.automation import engine
from crm.automation.models import Job, JobAttempt, Notification, Rule, RuleRun
from crm.automation.worker import Worker, execute, lease_next, recover_expired_leases, schedule_periodic
from crm.comms.models import OutboundMessage
from crm.contacts import services as contacts
from crm.core import clock
from crm.work import services as work
from tests.conftest import run_worker

pytestmark = pytest.mark.django_db
H = dt.timedelta(hours=1)
D = dt.timedelta(days=1)
DAYTIME = dt.datetime(2026, 11, 16, 3, 0, tzinfo=dt.UTC)  # 11:00 Asia/Shanghai (outside quiet hours)


def test_new_inquiry_notifies_current_handler_once(users, make_contact):
    with clock.frozen(DAYTIME):
        c = make_contact("Nina New", inquiry="Interested in the 2BR")
        run_worker()
        run_worker()
    notes = Notification.objects.filter(kind="inquiry", contact=c)
    assert [n.recipient for n in notes] == [users["ana"]]


def test_pool_inquiry_routes_to_coordinator_and_gap_is_visible(users, pool, make_contact):
    from crm.work.models import Pool

    orphan = Pool.objects.create(name="No coordinator pool")
    with clock.frozen(DAYTIME):
        a = make_contact("Pool Person", destination="pool", pool=pool, inquiry="Hi")
        b = make_contact("Orphan Person", destination="pool", pool=orphan, inquiry="Hi")
        run_worker()
    assert Notification.objects.get(kind="inquiry", contact=a).recipient == users["cora"]
    gap = Notification.objects.get(kind="inquiry", contact=b)
    assert gap.recipient is None and gap.status == "routing_gap"


def test_inquiry_ack_is_sandbox_captured_not_reported_as_delivered(users, make_contact, settings):
    with clock.frozen(DAYTIME):
        c = make_contact("Ella Email", email="ella@example.test", inquiry="Price list please")
        run_worker()
        run_worker()
    msg = OutboundMessage.objects.get(contact=c)
    assert msg.status == "sandbox_captured" and msg.status != "delivered"
    assert (settings.VAR_DIR / "sandbox_mail" / f"message-{msg.pk}.eml").exists()
    assert "Ella Email" in msg.body
    # Automated email is not human contact evidence.
    assert not c.interactions.exists()


def test_replayed_intake_event_does_not_duplicate_message(users, make_contact):
    with clock.frozen(DAYTIME):
        c = make_contact("Replay Rita", email="rita@example.test")
        contacts.record_inquiry(c, actor=users["ana"], message="Form A", channel="other", source=None, external_key="web-123")
        contacts.record_inquiry(c, actor=users["ana"], message="Form A", channel="other", source=None, external_key="web-123")
        run_worker()
        run_worker()
    assert c.inquiries.count() == 1
    assert OutboundMessage.objects.filter(contact=c).count() == 1


def test_customer_reply_before_send_suppresses_followup(users, make_contact):
    with clock.frozen(DAYTIME):
        rule = Rule.objects.get(key="customer-followup")
        rule.config = {"template": "inquiry-ack", "delay_minutes": 60}
        rule.save()
        c = make_contact("Ray Reply", email="ray@example.test", inquiry="Hello")
        run_worker()  # schedules the ack for +60 min
        contacts.record_interaction(c, actor=users["ana"], kind="inbound_reply", channel="email", summary="Customer wrote back",
                                    occurred_at=DAYTIME)
    with clock.frozen(DAYTIME + 2 * H):
        run_worker()
    msg = OutboundMessage.objects.get(contact=c)
    assert msg.status == "suppressed" and "replied" in msg.status_reason


def test_opt_out_suppresses_and_disabled_rule_cancels_queued(users, make_contact):
    with clock.frozen(DAYTIME):
        rule = Rule.objects.get(key="customer-followup")
        rule.config = {"template": "inquiry-ack", "delay_minutes": 30}
        rule.save()
        a = make_contact("Opt Out", email="o@example.test", inquiry="Hi")
        b = make_contact("Disabled Rule", email="d@example.test", inquiry="Hi")
        run_worker()
        contacts.set_email_opt_out(a, actor=users["ana"], opted_out=True)
        Rule.objects.filter(pk=rule.pk).update(enabled=False)
    with clock.frozen(DAYTIME + H):
        run_worker()
    assert OutboundMessage.objects.get(contact=a).status in ("suppressed", "cancelled")
    msg_b = OutboundMessage.objects.get(contact=b)
    assert msg_b.status == "cancelled" and "disabled" in msg_b.status_reason


def test_quiet_hours_defer_customer_message(users, make_contact):
    night = dt.datetime(2026, 11, 16, 14, 0, tzinfo=dt.UTC)  # 22:00 Asia/Shanghai
    with clock.frozen(night):
        c = make_contact("Night Owl", email="n@example.test", inquiry="Late question")
        run_worker()
        run_worker()
    msg = OutboundMessage.objects.get(contact=c)
    assert msg.status == "scheduled"
    assert msg.scheduled_for == dt.datetime(2026, 11, 17, 0, 0, tzinfo=dt.UTC)  # 08:00 local
    with clock.frozen(dt.datetime(2026, 11, 17, 0, 5, tzinfo=dt.UTC)):
        run_worker()
    msg.refresh_from_db()
    assert msg.status == "sandbox_captured"


def test_provider_timeout_is_uncertain_and_not_retried(users, make_contact):
    with clock.frozen(DAYTIME):
        c = make_contact("Tim Timeout", email="tim@timeout.invalid", inquiry="Hi")
        run_worker()
        run_worker()
    msg = OutboundMessage.objects.get(contact=c)
    assert msg.status == "uncertain"
    job = Job.objects.get(kind="comms.send")
    assert job.status == "succeeded" and job.attempts == 1


def test_provider_failure_retries_with_backoff_then_fails_visibly(users, make_contact):
    with clock.frozen(DAYTIME):
        c = make_contact("Fay Fail", email="fay@fail.invalid", inquiry="Hi")
        run_worker()
    job = Job.objects.get(kind="comms.send")
    assert job.status == "failed" and job.attempts == 1 and job.run_at > DAYTIME
    t = DAYTIME
    for _ in range(6):
        t += 2 * H
        with clock.frozen(t):
            run_worker()
    job.refresh_from_db()
    assert job.status == "dead" and job.attempts == job.max_attempts
    assert OutboundMessage.objects.get(contact=c).status == "failed"
    assert JobAttempt.objects.filter(job=job).count() == job.max_attempts


def test_worker_crash_lease_recovery_and_no_double_execution(users, make_contact):
    with clock.frozen(DAYTIME):
        make_contact("Crash Case", inquiry="Hi")
        job = lease_next("dead-worker", DAYTIME)  # leased by a worker that then "crashes"
        assert job is not None and job.status == "running"
        assert lease_next("other-worker", DAYTIME) is None or Job.objects.get(pk=job.pk).lease_owner == "dead-worker"
    later = DAYTIME + dt.timedelta(minutes=10)
    with clock.frozen(later):
        assert recover_expired_leases(later) == 1
        run_worker()
    job.refresh_from_db()
    assert job.status == "succeeded" and job.attempts == 2
    assert Notification.objects.filter(kind="inquiry").count() == 1


def test_persisted_reminder_survives_restart(users, make_contact):
    with clock.frozen(DAYTIME - 3 * D):
        c = make_contact("Restart Rosa")
        work.create_task(c, actor=users["ana"], assignee=users["ana"], title="Call Rosa", kind="call", due_at=DAYTIME - D)
    # A brand-new worker process (new object, new id) picks up the due sweep.
    with clock.frozen(DAYTIME):
        Worker(worker_id="fresh-after-restart", poll_seconds=0).run_once()
    assert Notification.objects.filter(kind="task_due", task__contact=c, recipient=users["ana"]).count() == 1


def test_sweep_is_idempotent_and_reassignment_reroutes(users, make_contact, policy):
    with clock.frozen(DAYTIME - 10 * D):
        c = make_contact("Reroute Rob")
        h = work.request_handover(c, actor=users["ana"], kind="transfer", recipient=users["ben"], reason="r",
                                  expected_version=1)
        work.accept_handover(h, actor=users["ben"])
    with clock.frozen(DAYTIME):
        engine.run_sweep(DAYTIME)
        first = Notification.objects.filter(kind="attention", contact=c).count()
        engine.run_sweep(DAYTIME)
    attention_notes = Notification.objects.filter(kind="attention", contact=c)
    assert attention_notes.count() == first >= 1
    assert {n.recipient for n in attention_notes} == {users["ben"]}


def test_escalation_without_recipients_records_routing_gap(users, make_contact):
    with clock.frozen(DAYTIME - 5 * D):
        c = make_contact("Esc Ed")
        work.create_task(c, actor=users["ana"], assignee=users["ana"], title="Overdue thing", kind="call",
                         due_at=DAYTIME - 4 * D)
    with clock.frozen(DAYTIME):
        engine.run_sweep(DAYTIME)
    gap = Notification.objects.get(kind="escalation")
    assert gap.status == "routing_gap"
    from crm.work.models import Assignment

    assert Assignment.objects.get(contact=c).user == users["ana"]  # never auto-removed


def test_watch_then_unwatch(users, make_contact):
    with clock.frozen(DAYTIME):
        c = make_contact("Watched Wendy")
        contacts.watch(c, actor=users["max"])
        contacts.record_interaction(c, actor=users["ana"], kind="conversation", channel="phone", summary="Chat",
                                    occurred_at=DAYTIME)
        run_worker()
        assert Notification.objects.filter(kind="watch", recipient=users["max"]).count() == 1
        contacts.unwatch(c, actor=users["max"])
        contacts.record_interaction(c, actor=users["ana"], kind="conversation", channel="phone", summary="Again",
                                    occurred_at=DAYTIME)
        run_worker()
    assert Notification.objects.filter(kind="watch", recipient=users["max"]).count() == 1
    from crm.work.models import Assignment

    assert Assignment.objects.get(contact=c).user == users["ana"]


def test_preview_has_no_side_effects(users, make_contact, policy):
    with clock.frozen(DAYTIME - 30 * D):
        make_contact("Preview Pat")
    before = (Notification.objects.count(), Job.objects.count(), RuleRun.objects.count())
    actions = engine.planned_sweep_actions(DAYTIME, policy)
    assert actions
    assert (Notification.objects.count(), Job.objects.count(), RuleRun.objects.count()) == before


def test_disabled_sweep_rule_creates_nothing(users, make_contact):
    Rule.objects.filter(key="inactivity").update(enabled=False)
    with clock.frozen(DAYTIME - 30 * D):
        make_contact("Disabled Dan")
    engine.run_sweep(DAYTIME)
    assert not Notification.objects.filter(rule__key="inactivity").exists()
    assert Notification.objects.filter(rule__key="missing-next").exists()  # other rules unaffected


def test_schedule_coalesces_missed_runs_and_digest_once_per_day(users, make_contact):
    with clock.frozen(DAYTIME - 30 * D):
        make_contact("Digest Dora")
    schedule_periodic(DAYTIME)
    schedule_periodic(DAYTIME + dt.timedelta(seconds=30))
    assert Job.objects.filter(kind="sweep.attention").count() == 1
    assert Job.objects.filter(kind="digest.daily").count() == 1
    with clock.frozen(DAYTIME):
        run_worker()
    with clock.frozen(DAYTIME + 3 * D):  # worker was down for days: one catch-up digest, not three
        run_worker()
    digests = Notification.objects.filter(kind="digest", recipient=users["ana"])
    assert digests.count() == 2


def test_unknown_job_kind_is_dead_lettered_not_looping(db):
    job = Job.objects.create(kind="nope", payload={})
    leased = lease_next("w", clock.now())
    assert execute(leased, "w") == "dead"
    job.refresh_from_db()
    assert job.status == "dead" and "No handler" in job.last_error
