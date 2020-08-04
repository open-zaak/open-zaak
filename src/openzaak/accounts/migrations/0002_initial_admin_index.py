# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.core.management import call_command
from django.db import migrations


def forward(apps, schema_editor):
    from django.apps import apps as django_apps
    from django.contrib.contenttypes.management import create_contenttypes

    apps = django_apps.get_app_configs()
    for app in apps:
        create_contenttypes(app)

    call_command("loaddata", "default_admin_index.json")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("admin_index", "0002_auto_20170802_1754"),
        ("besluiten", "0001_initial"),
        ("catalogi", "0001_initial"),
        ("documenten", "0001_initial"),
        ("notifications", "0009_auto_20190729_0427"),
        ("zaken", "0001_initial"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
