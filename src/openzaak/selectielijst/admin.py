# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin

from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin
from solo.admin import SingletonModelAdmin

from .models import ReferentieLijstConfig


@admin.register(ReferentieLijstConfig)
class ReferentieLijstConfigAdmin(DynamicArrayMixin, SingletonModelAdmin):
    list_display = ["service"]
