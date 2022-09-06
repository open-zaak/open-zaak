# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.db import migrations
from openzaak.utils.migrations import fill_service_urls


def fill_documenten_service_urls(apps, schema_editor):
    InformatieObject = apps.get_model("documenten", "EnkelvoudigInformatieObject")
    ObjectInformatieObject = apps.get_model("documenten", "ObjectInformatieObject")

    fill_service_urls(
        apps,
        InformatieObject,
        url_field="_informatieobjecttype_url",
        service_base_field="_informatieobjecttype_base_url",
        service_relative_field="_informatieobjecttype_relative_url",
    )
    fill_service_urls(
        apps,
        ObjectInformatieObject,
        url_field="_object_url",
        service_base_field="_object_base_url",
        service_relative_field="_object_relative_url",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("documenten", "0018_auto_20220906_1531"),
    ]

    operations = [
        migrations.RunPython(fill_documenten_service_urls, migrations.RunPython.noop)
    ]
