"""Load a synthetic demo workspace. All people and customers are fictional.

Customer addresses use reserved domains (example.test, fail.invalid, timeout.invalid)
and the email transport is the local sandbox, so nothing can reach a real person.
The demo password comes from CRM_DEMO_PASSWORD or is generated and printed once.
"""
from __future__ import annotations

import datetime as dt
import os
import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from crm.accounts.models import Team, User
from crm.automation.worker import Worker
from crm.contacts import services as contacts
from crm.contacts.models import Contact, Source
from crm.core import clock
from crm.core.reference import ensure_reference_data
from crm.core.services import get_policy
from crm.reporting.models import SpendEntry
from crm.work import services as work
from crm.work.models import Pool

H = dt.timedelta(hours=1)
D = dt.timedelta(days=1)

PEOPLE = [
    ("ana@demo.example.test", "Ana Reyes", "Sales agent", False),
    ("ben@demo.example.test", "Ben Santos", "Sales agent", False),
    ("cora@demo.example.test", "Cora Lim", "Team coordinator", False),
    ("max@demo.example.test", "Max Cruz", "Sales manager", False),
    ("admin@demo.example.test", "Ada Admin", "Workspace administrator", True),
]


class Command(BaseCommand):
    help = "Create a fictional demo workspace (refuses in production and on a non-empty database)."

    def add_arguments(self, parser):
        parser.add_argument("--no-worker", action="store_true", help="Do not run the worker after seeding")

    def handle(self, *args, **opts):
        if settings.CRM_ENV == "production":
            raise CommandError("Refusing to load demo data with CRM_ENV=production.")
        if Contact.objects.exists() or User.objects.exists():
            raise CommandError("The database already has users or contacts. Seed only a fresh database.")
        password = os.environ.get("CRM_DEMO_PASSWORD") or secrets.token_urlsafe(12)
        ensure_reference_data()
        now = clock.now()
        with transaction.atomic():
            u = self._people(password)
            self._story(u, now)
        if not opts["no_worker"]:
            Worker(worker_id="seed", poll_seconds=0).run_once()
        self.stdout.write(self.style.SUCCESS("Demo workspace ready. Accounts (all fictional):"))
        for email, name, title, _ in PEOPLE:
            self.stdout.write(f"  {email:28} {name} ({title})")
        if os.environ.get("CRM_DEMO_PASSWORD"):
            self.stdout.write("Password: the value of CRM_DEMO_PASSWORD.")
        else:
            self.stdout.write(f"Password for all demo accounts (shown once): {password}")

    def _people(self, password):
        team = Team.objects.create(name="North team")
        users = {}
        for email, name, title, admin in PEOPLE:
            user = User.objects.create_user(email, name, password, title=title, is_staff=admin)
            user.teams.add(team)
            users[email.split("@")[0]] = user
        Pool.objects.create(name="North team pool", team=team, coordinator=users["cora"], backup_coordinator=users["max"])
        return users

    def _story(self, u, now):
        ana, ben, cora, max_ = u["ana"], u["ben"], u["cora"], u["max"]
        pool = Pool.objects.get(name="North team pool")
        src = {s.code: s for s in Source.objects.all()}
        policy = get_policy()

        def capture(name, when, actor, *, destination="me", inquiry="", source="website", **data):
            with clock.frozen(when):
                return contacts.capture_contact(actor=actor, data={"display_name": name, "source": src[source], **data},
                                                destination=destination, pool=pool if destination == "pool" else None,
                                                inquiry_message=inquiry, inquiry_channel="email" if inquiry else "other").contact

        def log(contact, when, actor, kind, summary, channel="phone", inquiry=None):
            with clock.frozen(when):
                return contacts.record_interaction(contact, actor=actor, kind=kind, channel=channel, summary=summary,
                                                   occurred_at=when, inquiry=inquiry)

        def task(contact, when, actor, assignee, title, due, kind="follow_up", **kw):
            with clock.frozen(when):
                return work.create_task(contact, actor=actor, assignee=assignee, title=title, kind=kind, due_at=due, **kw)

        # Healthy relationship: recent call, next action scheduled.
        c = capture("Liam Navarro", now - 12 * D, ana, email="liam@example.test", phone="+63 917 555 0101",
                    interests="3BR house with garden, budget around 12M")
        log(c, now - 2 * D, ana, "conversation", "Discussed financing options; sending shortlist.")
        task(c, now - 2 * D, ana, ana, "Send shortlist of 3 garden homes", now + 2 * D)
        with clock.frozen(now - 2 * D):
            contacts.save_opportunity(
                c, actor=ana, opportunity=None, expected_version=None,
                data={"title": "Garden home shortlist", "stage": "viewing",
                      "amount_minor": 1_200_000_000, "currency": policy["currency"]},
            )

        # Overdue follow-up (task_overdue).
        c = capture("Sofia Mendoza", now - 9 * D, ana, email="sofia@example.test", source="referral",
                    interests="Condo near business district")
        log(c, now - 6 * D, ana, "conversation", "Wants to see two condos next week.")
        task(c, now - 6 * D, ana, ana, "Confirm viewing schedule", now - 2 * D, kind="call")

        # Toured, no follow-up recorded (toured_no_followup) - tour 3 days ago.
        c = capture("Marco Villanueva", now - 7 * D, ana, email="marco@example.test", source="walk-in")
        log(c, now - 3 * D, ana, "meeting_tour", "Toured Unit 12A and 15C. Liked 15C's view; concerned about parking.",
            channel="in_person")

        # Inquiry awaiting a response for 30 hours (inquiry_awaiting) + automated acknowledgement (sandbox).
        capture("Grace Tan", now - 30 * H, ana, email="grace@example.test",
                inquiry="Is the 2BR at Riverside still available? Can I visit Saturday?")

        # Acknowledgement that the sandbox provider rejects (failed message, visible in Messages).
        capture("Paolo Reyes", now - 5 * H, ben, email="paolo@fail.invalid", source="social",
                inquiry="Do you have pet-friendly rentals?")
        # Acknowledgement whose delivery is uncertain (timeout) - never auto-retried.
        capture("Iris Ocampo", now - 4 * H, ben, email="iris@timeout.invalid", source="search",
                inquiry="Please send the price list for the new tower.")

        # Waiting in the shared pool for more than a day (pool_waiting) and one fresh arrival.
        capture("Daniel Cruz", now - 40 * H, cora, destination="pool", source="roadshow", phone="+63 917 555 0144",
                inquiry="Met at the mall roadshow; interested in pre-selling units.")
        capture("Hannah Lee", now - 3 * H, cora, destination="pool", source="website", email="hannah@example.test")

        # Unaccepted handover: Ana asked Ben 30 hours ago (handover_waiting). Ana stays responsible.
        c = capture("Rafael Garcia", now - 15 * D, ana, email="rafael@example.test", source="referral", introducer=max_)
        log(c, now - 4 * D, ana, "conversation", "Prefers properties in Ben's district; open to a handover.")
        t = task(c, now - 4 * D, ana, ana, "Send updated listing for Eastwood", now + 1 * D)
        with clock.frozen(now - 30 * H):
            work.request_handover(c, actor=ana, kind="transfer", recipient=ben, reason="Ben covers Eastwood",
                                  context="Wants 2BR near the park. Budget 8-9M. Prefers evening calls.",
                                  task_dispositions={t.pk: "transfer"}, expected_version=c.assignment.version)

        # Inactive prospect (inactive) handled by Ben, with completed history.
        c = capture("Olivia Bautista", now - 40 * D, ben, email="olivia@example.test")
        with clock.frozen(now - 39 * D):
            contacts.set_lifecycle(c, actor=ben, lifecycle="prospect", disposition="active", reason="Qualified budget",
                                   expected_version=Contact.objects.get(pk=c.pk).version)
        log(c, now - 25 * D, ben, "conversation", "Budget confirmed; waiting for bonus in December.")
        done = task(c, now - 25 * D, ben, ben, "Share mortgage calculator", now - 24 * D)
        with clock.frozen(now - 24 * D):
            work.complete_task(done, actor=ben, note="Sent by email", expected_version=done.version)

        # Client with a won opportunity (lifecycle becomes client) and onboarding email.
        c = capture("Noah Aquino", now - 28 * D, ben, email="noah@example.test", source="referral")
        log(c, now - 20 * D, ben, "meeting_tour", "Toured model unit with spouse.", channel="in_person")
        with clock.frozen(now - 10 * D):
            opp = contacts.save_opportunity(c, actor=ben, opportunity=None, expected_version=None,
                                            data={"title": "Unit 8B purchase", "stage": "decision",
                                                  "amount_minor": 950_000_000, "currency": policy["currency"]})
            contacts.close_opportunity(opp, actor=ben, outcome="won", reason="Reservation signed",
                                       expected_version=opp.version, policy=policy)
        task(c, now - 10 * D, ben, ben, "Turn-over checklist call", now + 5 * D, kind="call")

        # Critical task for the manager.
        c = capture("Ethan Ramos", now - 6 * D, max_, email="ethan@example.test", source="other")
        log(c, now - 1 * D, max_, "outbound_attempt", "No answer; left voicemail.")
        task(c, now - 1 * D, max_, max_, "Resolve contract question before Friday", now + 12 * H, critical=True)

        # Opted-out lead: automated email is suppressed.
        c = capture("Mia Flores", now - 2 * D, ana, email="mia@example.test", inquiry="Just browsing for now.")
        with clock.frozen(now - 2 * D + H):
            contacts.set_email_opt_out(c, actor=ana, opted_out=True)

        # Marketing spend for the last full month and this month.
        first = now.date().replace(day=1)
        prev_end = first - D
        prev_start = prev_end.replace(day=1)
        for code, amount in (("social", 2_500_000), ("search", 4_000_000), ("roadshow", 6_000_000)):
            SpendEntry.objects.create(source=src[code], kind="actual", period_start=prev_start, period_end=prev_end,
                                      amount_minor=amount, currency=policy["currency"], note="Demo figure", created_by=max_)
            SpendEntry.objects.create(source=src[code], kind="planned", period_start=first, period_end=first + 27 * D,
                                      amount_minor=amount, currency=policy["currency"], note="Demo plan", created_by=max_)
