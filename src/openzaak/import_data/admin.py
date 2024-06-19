# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2024 Dimpact
from django.contrib import admin

from privates.admin import PrivateMediaMixin

from openzaak.import_data.models import Import


@admin.register(Import)
class ImportAdmin(PrivateMediaMixin, admin.ModelAdmin):
    model = Import

    list_display = (
        "uuid",
        "status",
        "import_type",
        "started_on",
        "finished_on",
    )

    list_filter = (
        "status",
        "import_type",
    )

    ordering = ("-created_on", "-finished_on")
