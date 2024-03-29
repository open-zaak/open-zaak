# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
# Generated by Django 3.2.14 on 2022-08-16 17:34

from django.db import migrations
import openzaak.utils.fields
import zgw_consumers.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ("zaken", "0012_auto_20220816_1726"),
    ]

    operations = [
        migrations.AddField(
            model_name="relevantezaakrelatie",
            name="_relevant_zaak_url",
            field=zgw_consumers.models.fields.ServiceUrlField(
                base_field="_relevant_zaak_base_url",
                blank=True,
                null=True,
                relative_field="_relevant_zaak_relative_url",
            ),
        ),
        migrations.AddField(
            model_name="resultaat",
            name="_resultaattype_url",
            field=zgw_consumers.models.fields.ServiceUrlField(
                base_field="_resultaattype_base_url",
                blank=True,
                null=True,
                relative_field="_resultaattype_relative_url",
            ),
        ),
        migrations.AddField(
            model_name="rol",
            name="_roltype_url",
            field=zgw_consumers.models.fields.ServiceUrlField(
                base_field="_roltype_base_url",
                blank=True,
                null=True,
                relative_field="_roltype_relative_url",
            ),
        ),
        migrations.AddField(
            model_name="status",
            name="_statustype_url",
            field=zgw_consumers.models.fields.ServiceUrlField(
                base_field="_statustype_base_url",
                blank=True,
                null=True,
                relative_field="_statustype_relative_url",
            ),
        ),
        migrations.AddField(
            model_name="zaak",
            name="_zaaktype_url",
            field=zgw_consumers.models.fields.ServiceUrlField(
                base_field="_zaaktype_base_url",
                blank=True,
                null=True,
                relative_field="_zaaktype_relative_url",
            ),
        ),
        migrations.AddField(
            model_name="zaakbesluit",
            name="_besluit_url",
            field=zgw_consumers.models.fields.ServiceUrlField(
                base_field="_besluit_base_url",
                blank=True,
                null=True,
                relative_field="_besluit_relative_url",
            ),
        ),
        migrations.AddField(
            model_name="zaakeigenschap",
            name="_eigenschap_url",
            field=zgw_consumers.models.fields.ServiceUrlField(
                base_field="_eigenschap_base_url",
                blank=True,
                null=True,
                relative_field="_eigenschap_relative_url",
            ),
        ),
        migrations.AddField(
            model_name="zaakinformatieobject",
            name="_informatieobject_url",
            field=zgw_consumers.models.fields.ServiceUrlField(
                base_field="_informatieobject_base_url",
                blank=True,
                null=True,
                relative_field="_informatieobject_relative_url",
            ),
        ),
        migrations.SeparateDatabaseAndState(
            # we don't do anything here, since they are not a DB fields
            state_operations=[
                migrations.AlterField(
                    model_name="relevantezaakrelatie",
                    name="url",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=False,
                        fk_field="_relevant_zaak",
                        null=False,
                        url_field="_relevant_zaak_url",
                    ),
                ),
                migrations.AlterField(
                    model_name="resultaat",
                    name="resultaattype",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=False,
                        fk_field="_resultaattype",
                        null=False,
                        url_field="_resultaattype_url",
                    ),
                ),
                migrations.AlterField(
                    model_name="rol",
                    name="roltype",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=False,
                        fk_field="_roltype",
                        null=False,
                        url_field="_roltype_url",
                    ),
                ),
                migrations.AlterField(
                    model_name="status",
                    name="statustype",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=False,
                        fk_field="_statustype",
                        null=False,
                        url_field="_statustype_url",
                    ),
                ),
                migrations.AlterField(
                    model_name="zaak",
                    name="zaaktype",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=False,
                        fk_field="_zaaktype",
                        null=False,
                        url_field="_zaaktype_url",
                    ),
                ),
                migrations.AlterField(
                    model_name="zaakbesluit",
                    name="besluit",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=False,
                        fk_field="_besluit",
                        null=False,
                        url_field="_besluit_url",
                    ),
                ),
                migrations.AlterField(
                    model_name="zaakeigenschap",
                    name="eigenschap",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=False,
                        fk_field="_eigenschap",
                        null=False,
                        url_field="_eigenschap_url",
                    ),
                ),
                migrations.AlterField(
                    model_name="zaakinformatieobject",
                    name="informatieobject",
                    field=openzaak.utils.fields.FkOrServiceUrlField(
                        blank=False,
                        fk_field="_informatieobject",
                        null=False,
                        url_field="_informatieobject_url",
                    ),
                ),
            ]
        ),
    ]
