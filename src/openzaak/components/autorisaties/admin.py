# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib import admin
from django.db import transaction
from django.forms import BaseModelFormSet
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from django_loose_fk.loaders import BaseLoader
from vng_api_common.authorizations.models import (
    Applicatie,
    AuthorizationsConfig,
    Autorisatie,
)
from vng_api_common.constants import ComponentTypes
from vng_api_common.models import JWTSecret
from zds_client import ClientAuth

from .admin_views import AutorisatiesView
from .forms import ApplicatieForm, CredentialsFormSet
from .models import AutorisatieSpec
from .utils import get_related_object

admin.site.unregister(AuthorizationsConfig)
admin.site.unregister(Applicatie)


class AutorisatieInline(admin.TabularInline):
    model = Autorisatie
    extra = 0
    fields = ["component", "scopes", "_get_extra"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def _get_extra(self, obj) -> str:
        """
        Show the context-dependent extra fields.

        An :class:`Autorisatie` requires extra attributes depending on the
        component that it's relevant for.

        .. note:: using get_resource_for_path spawns too many queries, since
            the viewsets have prefetch_related calls.
        """
        loader = BaseLoader()
        if obj.component == ComponentTypes.zrc:
            template = (
                "<strong>Zaaktype</strong>: "
                '<a href="{admin_url}" target="_blank" rel="noopener">{zt_repr}</a>'
                "<br>"
                "<strong>Maximale vertrouwelijkheidaanduiding</strong>: "
                "{va}"
            )
            if loader.is_local_url(obj.zaaktype):
                zaaktype = get_related_object(obj)
                admin_url = reverse(
                    "admin:catalogi_zaaktype_change", kwargs={"object_id": zaaktype.pk}
                )
                zt_repr = str(zaaktype)
            else:
                admin_url = obj.zaaktype
                zt_repr = f"{obj.zaaktype} (EXTERN)"

            return format_html(
                template,
                admin_url=admin_url,
                zt_repr=zt_repr,
                va=obj.get_max_vertrouwelijkheidaanduiding_display(),
            )

        if obj.component == ComponentTypes.drc:
            template = (
                "<strong>Informatieobjecttype</strong>: "
                '<a href="{admin_url}" target="_blank" rel="noopener">{iot_repr}</a>'
                "<br>"
                "<strong>Maximale vertrouwelijkheidaanduiding</strong>: "
                "{va}"
            )
            if loader.is_local_url(obj.informatieobjecttype):
                informatieobjecttype = get_related_object(obj)
                admin_url = reverse(
                    "admin:catalogi_informatieobjecttype_change",
                    kwargs={"object_id": informatieobjecttype.pk},
                )
                iot_repr = str(informatieobjecttype)
            else:
                admin_url = obj.informatieobjecttype
                iot_repr = f"{obj.informatieobjecttype} (EXTERN)"

            return format_html(
                template,
                admin_url=admin_url,
                iot_repr=iot_repr,
                va=obj.get_max_vertrouwelijkheidaanduiding_display(),
            )

        if obj.component == ComponentTypes.brc:
            template = (
                "<strong>Besluittype</strong>: "
                '<a href="{admin_url}" target="_blank" rel="noopener">{bt_repr}</a>'
            )
            if loader.is_local_url(obj.besluittype):
                besluittype = get_related_object(obj)
                admin_url = reverse(
                    "admin:catalogi_besluittype_change",
                    kwargs={"object_id": besluittype.pk},
                )
                bt_repr = str(besluittype)
            else:
                admin_url = obj.besluittype
                bt_repr = f"{obj.besluittype} (EXTERN)"

            return format_html(template, admin_url=admin_url, bt_repr=bt_repr,)

        return ""

    _get_extra.short_description = _("Extra parameters")


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

    def get_jwt(self, obj):
        if obj.identifier and obj.secret:
            auth = ClientAuth(obj.identifier, obj.secret)
            jwt = auth.credentials()["Authorization"]
            return format_html(
                '<code class="copy-action jwt" data-copy-value="{val}">{val}</code><p>{hint}</p>',
                val=jwt,
                hint=_("Gebruik het JWT-token nooit direct in een applicatie."),
            )
        return ""

    get_jwt.short_description = "jwt"


@admin.register(Applicatie)
class ApplicatieAdmin(admin.ModelAdmin):
    list_display = ("uuid", "client_ids", "label", "heeft_alle_autorisaties")
    readonly_fields = ("uuid",)
    form = ApplicatieForm
    inlines = (
        CredentialsInline,
        AutorisatieInline,
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
        return AutorisatiesView.as_view(admin_site=self.admin_site, model_admin=self,)

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


@admin.register(AutorisatieSpec)
class AutorisatieSpecAdmin(admin.ModelAdmin):
    list_display = (
        "applicatie",
        "component",
    )
    list_filter = ("component", "applicatie")
    search_fields = ("applicatie__uuid",)
