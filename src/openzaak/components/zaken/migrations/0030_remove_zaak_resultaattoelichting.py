# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
# Generated by Django 3.2.23 on 2024-01-18 15:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("zaken", "0029_auto_20230911_0810"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="zaak",
            name="resultaattoelichting",
        ),
    ]
