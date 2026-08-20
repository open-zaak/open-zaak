# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from maykin_common.accounts.admin import PreventPrivilegeEscalationMixin
from vng_api_common.authorizations.models import Applicatie, Autorisatie

from .models import User


def _excluded_permissions_qs():
    """
    Exclude replaced common_ground_api_common auth models.
    """
    app_ct = ContentType.objects.get_for_model(Applicatie)
    auth_ct = ContentType.objects.get_for_model(Autorisatie)
    return Permission.objects.exclude(content_type__in=[app_ct, auth_ct])


@admin.register(User)
class _UserAdmin(PreventPrivilegeEscalationMixin, UserAdmin):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "user_permissions" in form.base_fields:
            form.base_fields["user_permissions"].queryset = _excluded_permissions_qs()
        return form


class _GroupAdmin(GroupAdmin):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "permissions" in form.base_fields:
            form.base_fields["permissions"].queryset = _excluded_permissions_qs()
        return form


admin.site.unregister(Group)
admin.site.unregister(Applicatie)
admin.site.unregister(Autorisatie)
admin.site.register(Group, _GroupAdmin)
