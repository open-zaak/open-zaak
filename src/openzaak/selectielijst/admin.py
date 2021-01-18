# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin

from solo.admin import SingletonModelAdmin

from ..utils.admin import DynamicArrayMixin
from .models import ReferentieLijstConfig


@admin.register(ReferentieLijstConfig)
class ReferentieLijstConfigAdmin(DynamicArrayMixin, SingletonModelAdmin):
    list_display = ["api_root"]
