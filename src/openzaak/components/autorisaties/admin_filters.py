# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact
from django.contrib import admin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class InvalidApplicationsFilter(admin.SimpleListFilter):
    title = _("readiness")
    parameter_name = "readiness"

    def lookups(self, request, model_admin):
        return (
            ("valid", _("Valid only")),
            ("invalid", _("Invalid only")),
        )

    def queryset(self, request, queryset):
        invalid = Q(heeft_alle_autorisaties=False, has_authorizations=False) | Q(
            heeft_alle_autorisaties=True, has_authorizations=True
        )

        if self.value() == "invalid":
            return queryset.filter(invalid)

        if self.value() == "valid":
            return queryset.exclude(invalid)
