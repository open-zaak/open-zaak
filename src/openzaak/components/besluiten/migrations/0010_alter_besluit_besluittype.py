# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
# Generated by Django 3.2.14 on 2022-08-04 15:24

from django.db import migrations
import openzaak.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ("besluiten", "0009_auto_20220804_1523"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # we don't do anything here, since besluittype is not a DB field
            state_operations=[
                migrations.AlterField(
                    model_name="besluit",
                    name="besluittype",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=False,
                        fk_field="_besluittype",
                        null=False,
                        url_field="_besluittype_url",
                    ),
                ),
                migrations.AlterField(
                    model_name="besluit",
                    name="zaak",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=True, fk_field="_zaak", null=True, url_field="_zaak_url"
                    ),
                ),
                migrations.AlterField(
                    model_name="besluitinformatieobject",
                    name="informatieobject",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=False,
                        fk_field="_informatieobject",
                        null=False,
                        url_field="_informatieobject_url",
                    ),
                ),
            ]
        )
    ]
