# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
# Generated by Django 3.2.12 on 2022-03-18 16:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("config", "0012_delete_nlxconfig"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="internalservice",
            name="nlx",
        ),
    ]
