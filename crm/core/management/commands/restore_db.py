from django.core.management.base import BaseCommand, CommandError

from crm.core.backup import BackupError, restore_backup


class Command(BaseCommand):
    help = "Restore the database from a verified backup. Stop the web server and worker first."

    def add_arguments(self, parser):
        parser.add_argument("backup", help="Path to a .sqlite3 backup with its .json manifest")
        parser.add_argument("--confirm", default="", help="Must equal the backup file name")

    def handle(self, *args, **opts):
        try:
            safety = restore_backup(opts["backup"], confirm=opts["confirm"])
        except BackupError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS("Restore complete and integrity-checked."))
        if safety:
            self.stdout.write(f"The previous database was saved first as: {safety}")
        self.stdout.write("Run `python manage.py migrate` if the backup predates the current code.")
