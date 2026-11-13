from django.core.management.base import BaseCommand

from crm.core.backup_crypto import new_key


class Command(BaseCommand):
    help = "Print a new random backup encryption key for CRM_BACKUP_KEY. Store a copy away from the server."

    def handle(self, *args, **opts):
        self.stdout.write(new_key())
