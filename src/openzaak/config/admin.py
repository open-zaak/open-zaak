# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.conf import settings
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from drc_cmis.admin import CMISConfigAdmin as _CMISConfigAdmin
from drc_cmis.models import CMISConfig
from solo.admin import SingletonModelAdmin

from .models import FeatureFlags, InternalService, NLXConfig


@admin.register(NLXConfig)
class NLXConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(InternalService)
class InternalServiceAdmin(admin.ModelAdmin):
    list_display = ("api_type", "enabled", "nlx")


@admin.register(FeatureFlags)
class FeatureFlagsAdmin(SingletonModelAdmin):
    list_display = ("allow_unpublished_typen",)


# Replace the CMISConfigAdmin with our own.
admin.site.unregister(CMISConfig)


@admin.register(CMISConfig)
class CMISConfigAdmin(_CMISConfigAdmin):
    readonly_fields = _CMISConfigAdmin.readonly_fields + [
        "cmis_enabled",
    ]
    fieldsets = [
        (_("General"), {"fields": ("cmis_enabled", "cmis_connection",)},),
    ] + _CMISConfigAdmin.fieldsets[1:]

    def cmis_enabled(self, obj=None):
        return getattr(settings, "CMIS_ENABLED", False)

    cmis_enabled.short_description = _("Enabled")
    cmis_enabled.boolean = True

    def has_change_permission(self, *args, **kwargs):
        return self.cmis_enabled()
