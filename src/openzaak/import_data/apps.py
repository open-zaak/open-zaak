# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
from django.apps import AppConfig


class ImportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "openzaak.import_data"
