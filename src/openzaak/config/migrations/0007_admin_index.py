# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.db import migrations
from openzaak.utils.constants import COMPONENT_MAPPING


def fill_admin_index(apps, schema_editor):
    AppLink = apps.get_model("admin_index", "AppLink")
    AppGroup = apps.get_model("admin_index", "AppGroup")
    if (
        not AppLink.objects.filter(link="/admin/config/detail").exists()
        and AppGroup.objects.filter(slug="configuration").exists()
    ):
        app_group = AppGroup.objects.get(slug="configuration")
        AppLink.objects.create(
            link="/admin/config/detail",
            name="Service configuration",
            app_group=app_group,
            order=0,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("config", "0006_auto_20200327_1125"),
    ]

    operations = [migrations.RunPython(fill_admin_index, migrations.RunPython.noop)]
