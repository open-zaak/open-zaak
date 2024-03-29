# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
# Generated by Django 3.2.12 on 2022-03-10 22:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications_log", "0002_move_config_to_service_model"),
    ]

    operations = [
        migrations.AlterField(
            model_name="failednotification",
            name="message",
            field=models.JSONField(
                help_text="Content of the notification that was attempted to send.",
                verbose_name="notification message",
            ),
        ),
    ]
