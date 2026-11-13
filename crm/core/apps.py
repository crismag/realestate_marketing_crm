from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "crm.core"
    label = "core"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import checks  # noqa: F401  (registers deployment checks)
