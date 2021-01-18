# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.db import migrations


def rename(apps, schema_editor):
    AppLink = apps.get_model("admin_index", "applink")
    app_links = AppLink.objects.filter(link="/admin/config/nlx")
    for app_link in app_links:
        app_link.link = "/admin/config/nlx-inway"
        app_link.name = "NLX inway"
        app_link.save()


class Migration(migrations.Migration):
    dependencies = [
        ("config", "0001_initial"),
    ]

    operations = [migrations.RunPython(rename)]
