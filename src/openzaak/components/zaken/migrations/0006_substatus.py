# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
# Generated by Django 3.2.13 on 2022-04-19 14:31

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("zaken", "0005_auto_20220310_2216"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubStatus",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        help_text="Unieke resource identifier (UUID4)",
                        unique=True,
                    ),
                ),
                (
                    "tijdstip",
                    models.DateTimeField(
                        blank=True,
                        default=django.utils.timezone.now,
                        help_text="Het tijdstip waarop de STATUS de SUBSTATUS heeft verkregen.",
                    ),
                ),
                (
                    "omschrijving",
                    models.TextField(
                        help_text="Een, voor de initiator van de zaak relevante, toelichting op de substatus bij een hoofdstatus van een zaak.",
                        max_length=200,
                    ),
                ),
                (
                    "doelgroep",
                    models.CharField(
                        blank=True,
                        choices=[("betrokkenen", "betrokkenen"), ("intern", "Intern")],
                        db_index=True,
                        default="betrokkenen",
                        help_text="Indicatie van van de zichtbaarheid van een substatus.",
                        max_length=100,
                    ),
                ),
                (
                    "status",
                    models.ForeignKey(
                        blank=True,
                        help_text="URL-referentie naar de hoofdSTATUS.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="zaken.status",
                    ),
                ),
                (
                    "zaak",
                    models.ForeignKey(
                        help_text="URL-referentie naar de ZAAK.",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="zaken.zaak",
                    ),
                ),
            ],
            options={
                "verbose_name": "substatus",
                "verbose_name_plural": "substatussen",
            },
        ),
    ]