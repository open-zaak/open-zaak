# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.db import migrations
from openzaak.utils.migrations import fill_service_urls


def fill_besluiten_service_urls(apps, schema_editor):
    Besluit = apps.get_model("besluiten", "Besluit")
    BesluitInformatieObject = apps.get_model("besluiten", "BesluitInformatieObject")

    fill_service_urls(
        apps,
        Besluit,
        url_field="_zaak_url",
        service_base_field="_zaak_base_url",
        service_relative_field="_zaak_relative_url",
    )
    fill_service_urls(
        apps,
        Besluit,
        url_field="_besluittype_url",
        service_base_field="_besluittype_base_url",
        service_relative_field="_besluittype_relative_url",
    )
    fill_service_urls(
        apps,
        BesluitInformatieObject,
        url_field="_informatieobject_url",
        service_base_field="_informatieobject_base_url",
        service_relative_field="_informatieobject_relative_url",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("besluiten", "0007_auto_20220804_1522"),
    ]

    operations = [
        migrations.RunPython(fill_besluiten_service_urls, migrations.RunPython.noop)
    ]
