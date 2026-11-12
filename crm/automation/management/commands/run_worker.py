import datetime as dt

from django.core.management.base import BaseCommand, CommandError

from crm.automation.worker import Worker
from crm.core import clock


class Command(BaseCommand):
    help = "Run the durable background worker (reminders, notifications, digests, customer messages)."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process all currently due jobs, then exit.")
        parser.add_argument("--now", help="Deterministic clock for --once runs (ISO 8601 with offset), e.g. 2026-11-20T09:00:00+00:00")
        parser.add_argument("--sweep-now", action="store_true",
                            help="With --once: also run the attention sweep immediately instead of waiting for its schedule.")
        parser.add_argument("--max-minutes", type=float, help="Stop the long-running worker after this many minutes.")

    def handle(self, *args, **options):
        worker = Worker()
        if options["sweep_now"]:
            if not options["once"]:
                raise CommandError("--sweep-now is only allowed with --once")
            from crm.automation.queue import enqueue

            moment = dt.datetime.fromisoformat(options["now"]) if options["now"] else clock.now()
            enqueue("sweep.attention", {}, logical_key=f"sweep:manual:{moment.isoformat()}", max_attempts=3, run_at=moment)
        if options["now"]:
            if not options["once"]:
                raise CommandError("--now is only allowed with --once")
            try:
                moment = dt.datetime.fromisoformat(options["now"])
            except ValueError as exc:
                raise CommandError(f"Invalid --now: {exc}") from exc
            if moment.tzinfo is None:
                raise CommandError("--now needs a timezone offset, e.g. +00:00")
            with clock.frozen(moment):
                outcomes = worker.run_once()
            self.stdout.write(f"Processed at {moment.isoformat()}: {outcomes or 'nothing due'}")
            return
        if options["once"]:
            outcomes = worker.run_once()
            self.stdout.write(f"Processed: {outcomes or 'nothing due'}")
            return
        deadline = None
        if options["max_minutes"]:
            deadline = clock.now() + dt.timedelta(minutes=options["max_minutes"])
        worker.run_forever(deadline=deadline)
