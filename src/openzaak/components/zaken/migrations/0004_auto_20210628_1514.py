# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
# Generated by Django 2.2.24 on 2021-06-28 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zaken", "0003_auto_20200907_1207"),
    ]

    operations = [
        migrations.AlterField(
            model_name="zaak",
            name="identificatie",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="De unieke identificatie van de ZAAK binnen de organisatie die verantwoordelijk is voor de behandeling van de ZAAK.",
                max_length=40,
            ),
        ),
    ]
