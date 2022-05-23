# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.contrib import admin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class GeldigheidFilter(admin.SimpleListFilter):
    title = _("geldigheid")
    parameter_name = "validity"

    def lookups(self, request, model_admin):
        lookups = [
            ("currently", _("Now")),
            ("past", _("Past")),
            ("future", _("Future")),
        ]
        return lookups

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        today = timezone.now().date()
        if value == "currently":
            return queryset.filter(
                models.Q(datum_einde_geldigheid__isnull=True)
                | models.Q(datum_einde_geldigheid__gte=today),
                datum_begin_geldigheid__lte=today,
            )

        if value == "past":
            return queryset.filter(datum_einde_geldigheid__lt=today)

        if value == "future":
            return queryset.filter(datum_begin_geldigheid__gt=today)

        raise ValueError("Unknown lookup value")  # pragma: nocover
