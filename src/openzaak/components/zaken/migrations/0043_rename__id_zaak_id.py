# Generated by Django 4.2.19 on 2025-03-24 13:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("zaken", "0042_remove_zaak_identificatie_ptr_alter_zaak__id"),
    ]

    operations = [
        migrations.RenameField(
            model_name="zaak",
            old_name="_id",
            new_name="id",
        ),
    ]
