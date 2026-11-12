from django.db import migrations


def forwards(apps, schema_editor):
    from crm.core.reference import ensure_reference_data

    ensure_reference_data(apps)


class Migration(migrations.Migration):
    dependencies = [
        ("automation", "0001_initial"),
        ("comms", "0001_initial"),
        ("core", "0001_initial"),
        ("contacts", "0001_initial"),
    ]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
