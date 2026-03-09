from django.db import migrations


def create_defaults(apps, schema_editor):
    # No default types needed — sessions and questions are fully dynamic.
    # This migration is a placeholder for future seed data if required.
    pass


def reverse_defaults(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('clearance', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_defaults, reverse_defaults),
    ]