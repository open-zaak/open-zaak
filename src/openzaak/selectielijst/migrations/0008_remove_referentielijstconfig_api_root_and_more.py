# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
# Generated by Django 4.2.15 on 2024-10-31 10:42

from django.db import migrations, models
import django.db.models.deletion
import logging
from zgw_consumers.constants import APITypes

logger = logging.getLogger(__name__)


def set_selectielijst_service(apps, _):
    ReferentieLijstConfig = apps.get_model("selectielijst", "ReferentieLijstConfig")
    Service = apps.get_model("zgw_consumers", "Service")

    config, _ = ReferentieLijstConfig.objects.get_or_create()

    # This service should be created by `0003_move_config_to_service_model`
    svc, _ = Service.objects.get_or_create(
        api_root=config.api_root,
        defaults={
            "label": "VNG Selectielijst",
            "slug": "vng-selectielijst",
            "api_type": APITypes.orc,
            # No longer used, but still required by the admin
            "oas": config.api_root,
        },
    )

    config.service = svc
    config.save()


class Migration(migrations.Migration):

    dependencies = [
        ("zgw_consumers", "0022_set_default_service_slug"),
        ("selectielijst", "0007_alter_referentielijstconfig_default_year"),
    ]

    operations = [
        migrations.AddField(
            model_name="referentielijstconfig",
            name="service",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"api_type": "orc"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="zgw_consumers.service",
                verbose_name="Referentielijsten API service",
            ),
        ),
        migrations.RunPython(set_selectielijst_service, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="referentielijstconfig",
            name="api_root",
        ),
    ]
