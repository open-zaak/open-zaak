# Generated by Django 4.2.15 on 2024-10-09 08:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("config", "0016_cloudeventconfig"),
    ]

    operations = [
        migrations.RenameField(
            model_name="cloudeventconfig",
            old_name="type",
            new_name="zaak_create_event_type",
        ),
    ]
