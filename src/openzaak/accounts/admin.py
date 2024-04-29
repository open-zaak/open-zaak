# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, Permission
from django.template.response import TemplateResponse
from django.urls import path

from .models import User


@admin.register(User)
class _UserAdmin(UserAdmin):
    change_list_template = "admin/accounts/change_list_user.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "authorization-matrix/",
                self.admin_site.admin_view(self.authorization_matrix),
                name="authorization_matrix",
            )
        ]
        return my_urls + urls

    def authorization_matrix(self, request):
        context = dict(self.admin_site.each_context(request))
        ADMIN_GROUPS = list(
            Group.objects.order_by("name").values_list("name", flat=True)
        )
        EMPLOYEE_COLUMNS = [
            "Naam",
            "E-mail",
            "Laatst gewijzigd",
            "Actief",
            "Admin toegang",
            "Admin supergebruiker",
        ] + ADMIN_GROUPS
        context["user_matrix_headings"] = EMPLOYEE_COLUMNS
        context["user_matrix"] = get_user_group_matrix(ADMIN_GROUPS)
        ADMIN_PERMS_COLUMNS = ["Module", "Actie"] + ADMIN_GROUPS
        context["permission_matrix_headings"] = ADMIN_PERMS_COLUMNS
        context["permission_matrix"] = get_permission_group_matrix(ADMIN_GROUPS)
        return TemplateResponse(
            request, "admin/accounts/authorization_matrix.html", context
        )


def get_user_group_matrix(admin_groups: list):
    matrix = []
    for user in User.objects.prefetch_related("groups"):
        data = [
            user.get_full_name(),
            user.email,
            user.last_login.strftime("%Y-%m-%d"),
            user.is_active,
            user.is_staff,
            user.is_superuser,
        ]
        active_groups = [g.name for g in user.groups.all()]
        data += [(g in active_groups) for g in admin_groups]
        matrix.append(data)
    return matrix


def get_permission_group_matrix(admin_groups: list):
    groups = Group.objects.prefetch_related("permissions").order_by("name")
    matrix = []
    for p in Permission.objects.prefetch_related("content_type").order_by(
        "content_type__app_label", "name"
    ):
        data = [
            p.content_type.app_label,
            p.name,
        ]
        data += [(p in g.permissions.all()) for g in groups]
        matrix.append(data)
    return matrix
