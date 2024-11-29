# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.forms import BaseModelFormSet
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from vng_api_common.authorizations.models import (
    Applicatie,
    AuthorizationsConfig,
    Autorisatie,
)
from vng_api_common.authorizations.utils import generate_jwt
from vng_api_common.models import JWTSecret

from .admin_filters import InvalidApplicationsFilter
from .admin_views import AutorisatiesView
from .forms import ApplicatieForm, CredentialsFormSet
from .models import CatalogusAutorisatie

admin.site.unregister(AuthorizationsConfig)
admin.site.unregister(Applicatie)


class CredentialsInline(admin.TabularInline):
    model = JWTSecret
    formset = BaseModelFormSet
    fields = (
        "identifier",
        "secret",
        "get_jwt",
    )
    readonly_fields = ("get_jwt",)
    classes = ["client-credentials"]
    extra = 1

    # Disable system checks, since this model is not related at all to Applicatie
    def check(self, *args, **kwargs):
        return []

    def get_formset(self, request, obj=None, **kwargs):
        return CredentialsFormSet

    @admin.display(description="jwt")
    def get_jwt(self, obj):
        if obj.identifier and obj.secret:
            jwt = generate_jwt(
                obj.identifier, obj.secret, obj.identifier, obj.identifier
            )
            return format_html(
                '<code class="copy-action jwt" data-copy-value="{val}">{val}</code><p>{hint}</p>',
                val=jwt,
                hint=_("Gebruik het JWT-token nooit direct in een applicatie."),
            )
        return ""


@admin.register(Applicatie)
class ApplicatieAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "client_ids",
        "label",
        "heeft_alle_autorisaties",
        "ready",
        "hints",
    )
    list_filter = (
        "heeft_alle_autorisaties",
        InvalidApplicationsFilter,
    )
    readonly_fields = ("uuid",)
    form = ApplicatieForm
    inlines = (CredentialsInline,)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        autorisaties = Autorisatie.objects.filter(applicatie=OuterRef("pk"))
        catalogus_autorisaties = CatalogusAutorisatie.objects.filter(
            applicatie=OuterRef("pk")
        )
        return qs.annotate(
            has_authorizations=Exists(autorisaties) | Exists(catalogus_autorisaties)
        )

    def get_urls(self) -> list:
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/autorisaties/",
                self.admin_site.admin_view(self.autorisaties_view),
                name="authorizations_applicatie_autorisaties",
            ),
        ]
        return custom_urls + urls

    @property
    def autorisaties_view(self):
        return AutorisatiesView.as_view(
            admin_site=self.admin_site,
            model_admin=self,
        )

    def response_post_save_change(self, request, obj):
        if "_autorisaties" in request.POST:
            return redirect(
                "admin:authorizations_applicatie_autorisaties", object_id=obj.id
            )
        return super().response_post_save_change(request, obj)

    @transaction.atomic
    def delete_model(self, request, obj):
        secrets = JWTSecret.objects.filter(identifier__in=obj.client_ids)
        secrets.delete()
        super().delete_model(request, obj)

    @transaction.atomic
    def delete_queryset(self, request, queryset):
        """Given a queryset, delete it from the database."""
        client_ids = queryset.values_list("client_ids", flat=True)
        client_ids = sum(list(client_ids), [])

        secrets = JWTSecret.objects.filter(identifier__in=client_ids)
        secrets.delete()

        super().delete_queryset(request, queryset)

    @admin.display(
        description=_("Ready?"),
        boolean=True,
    )
    def ready(self, obj) -> bool:
        return obj.heeft_alle_autorisaties ^ obj.has_authorizations

    @admin.display(description=_("Hints"))
    def hints(self, obj) -> str:
        if self.ready(obj):
            return ""

        if obj.heeft_alle_autorisaties and obj.has_authorizations:
            return _(
                "An application must either have 'all permissions' checked, or have "
                "explicit authorizations, but not both."
            )

        if not obj.heeft_alle_autorisaties and not obj.has_authorizations:
            return _(
                "An application must either have 'all permissions' checked, or have "
                "explicit authorizations assigned. Nothing is set now."
            )

        return ""


@admin.register(CatalogusAutorisatie)
class CatalogusAutorisatieAdmin(admin.ModelAdmin):
    list_display = (
        "applicatie",
        "component",
        "catalogus",
    )
    list_filter = ("component", "applicatie", "catalogus")
    search_fields = (
        "applicatie__uuid",
        "catalogus__naam",
    )
