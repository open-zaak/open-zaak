# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "openzaak.accounts"

    def ready(self):
        from . import metrics  # noqa
        from . import signals  # noqa
