from django.core.management.base import BaseCommand, CommandError

from crm.core.backup import BackupError, create_backup, prune_backups, verify_backup


class Command(BaseCommand):
    help = "Take a consistent online backup of the SQLite database (integrity-checked, 0600, with manifest)."

    def add_arguments(self, parser):
        parser.add_argument("--dir", help="Backup directory (default CRM_BACKUP_DIR)")
        parser.add_argument("--verify", metavar="FILE", help="Only verify an existing backup")
        parser.add_argument("--keep", type=int, default=0, help="After backing up, keep only the newest N backups")

    def handle(self, *args, **opts):
        try:
            if opts["verify"]:
                manifest = verify_backup(opts["verify"])  # decrypts to a temporary file when encrypted
                self.stdout.write(self.style.SUCCESS(f"Backup OK: {manifest['file']} sha256={manifest['sha256'][:16]}…"))
                return
            path = create_backup(opts["dir"])
        except BackupError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Backup written: {path}"))
        if not path.name.endswith(".enc"):
            self.stdout.write("Note: this backup is NOT encrypted. Set CRM_BACKUP_KEY (see `manage.py backup_key`).")
        if opts["keep"]:
            for old in prune_backups(opts["dir"], keep=opts["keep"]):
                self.stdout.write(f"Pruned {old.name}")
