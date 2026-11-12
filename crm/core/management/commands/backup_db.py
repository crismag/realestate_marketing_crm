from django.core.management.base import BaseCommand, CommandError

from crm.core.backup import BackupError, create_backup, verify_backup


class Command(BaseCommand):
    help = "Take a consistent online backup of the SQLite database (integrity-checked, 0600, with manifest)."

    def add_arguments(self, parser):
        parser.add_argument("--dir", help="Backup directory (default CRM_BACKUP_DIR)")
        parser.add_argument("--verify", metavar="FILE", help="Only verify an existing backup")

    def handle(self, *args, **opts):
        try:
            if opts["verify"]:
                manifest = verify_backup(opts["verify"])
                self.stdout.write(self.style.SUCCESS(f"Backup OK: {manifest['file']} sha256={manifest['sha256'][:16]}…"))
                return
            path = create_backup(opts["dir"])
        except BackupError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Backup written: {path}"))
        self.stdout.write("Note: backups are not encrypted. Store them on encrypted, access-controlled storage.")
