# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
# Generated by Django 3.2.14 on 2022-09-06 15:46

from django.db import migrations
import openzaak.utils.fields
import zgw_consumers.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ("documenten", "0020_auto_20220906_1542"),
    ]

    operations = [
        migrations.AddField(
            model_name="enkelvoudiginformatieobject",
            name="_informatieobjecttype_url",
            field=zgw_consumers.models.fields.ServiceUrlField(
                base_field="_informatieobjecttype_base_url",
                blank=True,
                null=True,
                relative_field="_informatieobjecttype_relative_url",
            ),
        ),
        migrations.AddField(
            model_name="objectinformatieobject",
            name="_object_url",
            field=zgw_consumers.models.fields.ServiceUrlField(
                base_field="_object_base_url",
                blank=True,
                null=True,
                relative_field="_object_relative_url",
            ),
        ),
        migrations.SeparateDatabaseAndState(
            # we don't do anything here, since they are not DB fields
            state_operations=[
                migrations.AlterField(
                    model_name="enkelvoudiginformatieobject",
                    name="informatieobjecttype",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=False,
                        fk_field="_informatieobjecttype",
                        null=False,
                        url_field="_informatieobjecttype_url",
                    ),
                ),
                migrations.AlterField(
                    model_name="objectinformatieobject",
                    name="besluit",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=True,
                        fk_field="_besluit",
                        null=True,
                        url_field="_object_url",
                    ),
                ),
                migrations.AlterField(
                    model_name="objectinformatieobject",
                    name="zaak",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=True, fk_field="_zaak", null=True, url_field="_object_url"
                    ),
                ),
            ]
        ),
    ]
