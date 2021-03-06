# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
# Generated by Django 2.2.10 on 2020-08-17 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogi", "0004_auto_20200605_1415"),
    ]

    operations = [
        migrations.AddField(
            model_name="zaaktype",
            name="selectielijst_procestype_jaar",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Het jaartal waartoe het procestype behoort.",
                null=True,
            ),
        ),
    ]
