# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Open Zaak maintainers
from django.contrib import admin

from ..models import ZaakIdentificatie


@admin.register(ZaakIdentificatie)
class ZaakIdentificatieAdmin(admin.ModelAdmin):
    list_display = ("identificatie", "bronorganisatie")
    search_fields = ("identificatie",)
    list_filter = ("bronorganisatie",)
