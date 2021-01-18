# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = "openzaak.utils"

    def ready(self):
        from . import checks  # noqa
