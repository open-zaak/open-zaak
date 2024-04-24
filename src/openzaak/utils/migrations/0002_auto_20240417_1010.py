# Generated by Django 3.2.23 on 2024-04-17 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("utils", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="import",
            name="import_file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="import/import-files/",
                verbose_name="Import metadata bestand",
            ),
        ),
        migrations.AlterField(
            model_name="import",
            name="report_file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="import/report-files/",
                verbose_name="Reportage bestand",
            ),
        ),
    ]