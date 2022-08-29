# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
# Generated by Django 3.2.14 on 2022-08-18 16:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("zgw_consumers", "0015_auto_20220307_1522"),
        ("documenten", "0006_alter_enkelvoudiginformatieobject__informatieobjecttype"),
    ]

    operations = [
        migrations.AddField(
            model_name="enkelvoudiginformatieobject",
            name="_informatieobjecttype_base_url",
            field=models.ForeignKey(
                blank=True,
                help_text="Basis deel van URL-referentie naar extern INFORMATIEOBJECTTYPE (in een andere Catalogi API).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="zgw_consumers.service",
            ),
        ),
        migrations.AddField(
            model_name="enkelvoudiginformatieobject",
            name="_informatieobjecttype_relative_url",
            field=models.CharField(
                blank=True,
                help_text="Relatief deel van URL-referentie naar extern INFORMATIEOBJECTTYPE (in een andere Catalogi API).",
                max_length=200,
                null=True,
                verbose_name="informatieobjecttype relative url",
            ),
        ),
        migrations.AddField(
            model_name="objectinformatieobject",
            name="_besluit_base_url",
            field=models.ForeignKey(
                blank=True,
                help_text="Basis deel van URL-referentie naar extern BESLUIT (in een andere Besluiten API).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="oio_besluiten",
                to="zgw_consumers.service",
            ),
        ),
        migrations.AddField(
            model_name="objectinformatieobject",
            name="_besluit_relative_url",
            field=models.CharField(
                blank=True,
                help_text="Relatief deel van URL-referentie naar extern BESLUIT (in een andere Besluiten API).",
                max_length=200,
                null=True,
                verbose_name="besluit relative url",
            ),
        ),
        migrations.AddField(
            model_name="objectinformatieobject",
            name="_zaak_base_url",
            field=models.ForeignKey(
                blank=True,
                help_text="Basis deel van URL-referentie naar extern ZAAK (in een andere Zaken API).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="oio_zaken",
                to="zgw_consumers.service",
            ),
        ),
        migrations.AddField(
            model_name="objectinformatieobject",
            name="_zaak_relative_url",
            field=models.CharField(
                blank=True,
                help_text="Relatief deel van URL-referentie naar extern ZAAK (in een andere Zaken API).",
                max_length=200,
                null=True,
                verbose_name="zaak relative url",
            ),
        ),
    ]
