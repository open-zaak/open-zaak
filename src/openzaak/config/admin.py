# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib import admin

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
