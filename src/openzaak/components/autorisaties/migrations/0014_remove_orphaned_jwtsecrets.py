# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
from django.db import migrations
import logging

logger = logging.getLogger(__name__)


def forward(apps, schema_editor):
    JWTSecret = apps.get_model("vng_api_common", "JWTSecret")
    Applicatie = apps.get_model("authorizations", "Applicatie")

    client_ids = Applicatie.objects.exclude(client_ids=[]).values_list(
        "client_ids", flat=True
    )
    client_ids = sum(list(client_ids), [])
    deleted, count = JWTSecret.objects.exclude(identifier__in=client_ids).delete()

    if count:
        logger.info(f"{count} orphaned JWTSecret objects have been deleted")


class Migration(migrations.Migration):

    dependencies = [
        ("autorisaties", "0013_alter_catalogusautorisatie_component"),
        ("vng_api_common", "0005_auto_20190614_1346"),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
