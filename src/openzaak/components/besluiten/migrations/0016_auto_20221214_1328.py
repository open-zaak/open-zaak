# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
# Generated by Django 3.2.16 on 2022-12-14 13:28

import django.db.models.deletion
from django.db import migrations, models

import openzaak.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ("zaken", "0020_auto_20221214_1259"),
        ("besluiten", "0015_auto_20221214_1318"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="besluit",
                    name="zaak",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=True, fk_field="_zaak", null=True, url_field="_zaak_url"
                    ),
                ),
            ],
        ),
        migrations.AlterField(
            model_name="besluit",
            name="_zaak",
            field=models.ForeignKey(
                blank=True,
                help_text="URL-referentie naar de ZAAK (in de Zaken API) waarvan dit besluit uitkomst is.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="zaken.zaak",
            ),
        ),
    ]
