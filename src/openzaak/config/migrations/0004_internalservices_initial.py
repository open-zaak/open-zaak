# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.db import migrations
from openzaak.utils.constants import COMPONENT_MAPPING


def initial(apps, schema_editor):
    InternalService = apps.get_model("config", "InternalService")
    for component, api_type in COMPONENT_MAPPING.items():
        InternalService.objects.create(api_type=api_type)


class Migration(migrations.Migration):
    dependencies = [
        ("config", "0003_internalservice"),
    ]

    operations = [migrations.RunPython(initial, migrations.RunPython.noop)]
