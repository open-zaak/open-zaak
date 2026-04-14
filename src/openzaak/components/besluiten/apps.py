# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.apps import AppConfig


class BesluitenConfig(AppConfig):
    name = "openzaak.components.besluiten"

    def ready(self) -> None:
        from . import signals  # noqa
