# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from django.contrib import admin

from openzaak.import_data.models import Import


@admin.register(Import)
class ImportAdmin(admin.ModelAdmin):
    model = Import
