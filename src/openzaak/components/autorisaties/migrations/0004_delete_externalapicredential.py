# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
# Generated by Django 2.2.10 on 2020-03-27 11:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("autorisaties", "0003_fill_service"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ExternalAPICredential",
        ),
    ]
