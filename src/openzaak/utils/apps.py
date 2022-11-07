# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.apps import AppConfig
from django.db.models.signals import post_migrate


class UtilsConfig(AppConfig):
    name = "openzaak.utils"

    def ready(self):
        from . import checks  # noqa
        from .signals import update_admin_index

        post_migrate.connect(update_admin_index, sender=self)
