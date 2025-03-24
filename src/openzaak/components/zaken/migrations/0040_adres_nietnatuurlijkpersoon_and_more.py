# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
# Generated by Django 4.2.19 on 2025-03-24 10:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("zaken", "0039_rol_begin_geldigheid_rol_einde_geldigheid"),
    ]

    operations = [
        migrations.AddField(
            model_name="adres",
            name="nietnatuurlijkpersoon",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="verblijfsadres",
                to="zaken.nietnatuurlijkpersoon",
            ),
        ),
        migrations.AddField(
            model_name="nietnatuurlijkpersoon",
            name="vestigings_nummer",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="**EXPERIMENTEEL** Een korte unieke aanduiding van de Vestiging.",
                max_length=24,
            ),
        ),
    ]
