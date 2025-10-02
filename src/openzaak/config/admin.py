# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.conf import settings
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from drc_cmis.admin import CMISConfigAdmin as _CMISConfigAdmin
from drc_cmis.models import CMISConfig
from solo.admin import SingletonModelAdmin

from .models import CloudEventConfig, FeatureFlags, InternalService


@admin.register(InternalService)
class InternalServiceAdmin(admin.ModelAdmin):
    list_display = (
        "api_type",
        "enabled",
    )


@admin.register(FeatureFlags)
class FeatureFlagsAdmin(SingletonModelAdmin):
    list_display = ("allow_unpublished_typen",)


@admin.register(CloudEventConfig)
class CloudEventConfigAdmin(SingletonModelAdmin):
    pass


# Replace the CMISConfigAdmin with our own.
admin.site.unregister(CMISConfig)


@admin.register(CMISConfig)
class CMISConfigAdmin(_CMISConfigAdmin):
    readonly_fields = _CMISConfigAdmin.readonly_fields + [
        "cmis_enabled",
    ]
    fieldsets = [
        (
            _("General"),
            {
                "fields": (
                    "cmis_enabled",
                    "cmis_connection",
                )
            },
        ),
    ] + _CMISConfigAdmin.fieldsets[1:]

    @admin.display(
        description=_("Enabled"),
        boolean=True,
    )
    def cmis_enabled(self, obj=None):
        return getattr(settings, "CMIS_ENABLED", False)

    def has_change_permission(self, *args, **kwargs):
        return self.cmis_enabled()
