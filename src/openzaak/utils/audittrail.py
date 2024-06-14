# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin
from django.http import HttpRequest

from vng_api_common.audittrails.admin import AuditTrailAdmin as VNGAuditTrailAdmin
from vng_api_common.audittrails.models import AuditTrail

admin.site.unregister(AuditTrail)


@admin.register(AuditTrail)
class AuditTrailAdmin(VNGAuditTrailAdmin):
    list_display = (
        "uuid",
        "resource",
        "actie",
        "bron",
        "resultaat",
        "applicatie_weergave",
    )
    list_filter = ("bron", "resource", "actie", "applicatie_id", "resultaat")

    def has_change_permission(self, request: HttpRequest, obj=None):
        return False

    def has_add_permission(self, request: HttpRequest):
        return False
