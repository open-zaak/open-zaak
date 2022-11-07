# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from io import StringIO

from django.apps import apps
from django.contrib.contenttypes.management import create_contenttypes
from django.core.management import call_command

from django_admin_index.models import AppGroup


def update_admin_index(sender, **kwargs):
    AppGroup.objects.all().delete()

    # Make sure project models are registered.
    project_name = __name__.split(".")[0]

    for app_config in apps.get_app_configs():
        if app_config.name.startswith(project_name):
            create_contenttypes(app_config, verbosity=0)

    call_command("loaddata", "default_admin_index", verbosity=0, stdout=StringIO())
