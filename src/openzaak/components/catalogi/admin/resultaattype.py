# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Optional, Union

from django.contrib import admin
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from vng_api_common.client import Client, to_internal_data
from zgw_consumers.client import build_client

from openzaak.selectielijst.admin_fields import (
    get_resultaat_readonly_field,
    get_resultaattype_omschrijving_field,
    get_resultaattype_omschrijving_readonly_field,
    get_selectielijstklasse_field,
)
from openzaak.selectielijst.models import ReferentieLijstConfig
from openzaak.utils.admin import UUIDAdminMixin

from ..models import ResultaatType, ZaakType
from .forms import ResultaatTypeForm
from .mixins import CatalogusContextAdminMixin, ReadOnlyPublishedZaaktypeMixin


@admin.register(ResultaatType)
class ResultaatTypeAdmin(
    ReadOnlyPublishedZaaktypeMixin,
    UUIDAdminMixin,
    CatalogusContextAdminMixin,
    admin.ModelAdmin,
):
    model = ResultaatType
    form = ResultaatTypeForm

    # List
    list_display = (
        "omschrijving",
        "omschrijving_generiek",
        "selectielijstklasse",
    )
    list_filter = ("zaaktype",)
    ordering = ("zaaktype", "omschrijving")
    search_fields = (
        "uuid",
        "omschrijving",
        "omschrijving_generiek",
        "selectielijstklasse",
        "toelichting",
    )

    # Details
    fieldsets = (
        (
            _("Algemeen"),
            {
                "fields": (
                    "zaaktype",
                    "omschrijving",
                    "omschrijving_generiek",
                    "toelichting",
                    "datum_begin_geldigheid",
                    "datum_einde_geldigheid",
                )
            },
        ),
        (
            _("Gemeentelijke selectielijst"),
            {
                "fields": (
                    "get_zaaktype_procestype",
                    "resultaattypeomschrijving",
                    "selectielijstklasse",
                )
            },
        ),
        (
            _("Archief"),
            {"fields": ("archiefnominatie", "archiefactietermijn")},
        ),
        (
            _("Bepaling brondatum archiefprocedure"),
            {
                "fields": (
                    "brondatum_archiefprocedure_afleidingswijze",
                    "brondatum_archiefprocedure_datumkenmerk",
                    "brondatum_archiefprocedure_einddatum_bekend",
                    "brondatum_archiefprocedure_objecttype",
                    "brondatum_archiefprocedure_registratie",
                    "brondatum_archiefprocedure_procestermijn",
                )
            },
        ),
        (_("Relaties"), {"fields": ("zaakobjecttypen",)}),
    )
    raw_id_fields = (
        "zaaktype",
        "zaakobjecttypen",
        "informatieobjecttypen",
        "besluittypen",
    )
    readonly_fields = ("get_zaaktype_procestype", "omschrijving_generiek")

    def _get_zaaktype(
        self, request: HttpRequest, obj: Optional[ResultaatType] = None
    ) -> Union[ZaakType, None]:
        """
        Track the relevant zaaktype so that we can display/filter information.

        This caches the _zaaktype on the request object, as the model admin instance
        is created only once and re-used for different requests (= not thread safe!). By
        setting the attribute on the request, we cache it for that request only.

        The zaaktype is read in get_form, which generates a ModelForm class for every
        request, so that's thread-safe. This is used in the form class to then set the
        zaaktype for the ResultaatType form instance, which in turn is used to render
        the read-only fields.

        The Django admin code is a bit of a mess to be honest. /sadface
        """
        if not hasattr(request, "_zaaktype"):
            object_id = request.resolver_match.kwargs.get("object_id")
            container = request.POST if request.method == "POST" else request.GET
            zaaktype_pk = container.get("zaaktype")

            # fetch it from the instance we're viewing/editing if possible
            if obj is not None:
                zaaktype = obj.zaaktype
            elif object_id is not None:
                resultaattype = self.get_object(request, object_id)
                zaaktype = resultaattype.zaaktype
            # e.g. on create, fetch it from the URL param
            elif zaaktype_pk:
                zaaktype = ZaakType.objects.filter(pk=zaaktype_pk).first()
            else:
                zaaktype = None

            request._zaaktype = zaaktype

        return request._zaaktype

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        form._zaaktype = self._get_zaaktype(request, obj=obj)
        return form

    @admin.display(description="zaaktype procestype")
    def get_zaaktype_procestype(self, obj):
        # obj is form.instance here
        if not obj.zaaktype_id:
            return _(
                "Please save this Resultaattype first to get proper filtering of selectielijstklasses"
            )
        url = obj.zaaktype.selectielijst_procestype
        if not url:
            return _(
                "Please select a Procestype for the related ZaakType to "
                "get proper filtering of selectielijstklasses"
            )
        config = ReferentieLijstConfig.get_solo()
        assert config.service
        client = build_client(config.service, Client)
        procestype = to_internal_data(client.get(url))
        return f"{procestype['nummer']} - {procestype['naam']}"

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        zaaktype = self._get_zaaktype(request)

        if db_field.name == "selectielijstklasse":
            if zaaktype is not None:
                kwargs["procestype"] = zaaktype.selectielijst_procestype
            return get_selectielijstklasse_field(db_field, request, **kwargs)

        if db_field.name == "resultaattypeomschrijving":
            return get_resultaattype_omschrijving_field(db_field, request, **kwargs)

        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def render_readonly(self, field, result_repr, value):
        if not value:
            return super().render_readonly(field, result_repr, value)

        if field.name == "selectielijstklasse":
            res = get_resultaat_readonly_field(value)
            return res

        if field.name == "resultaattypeomschrijving":
            res = get_resultaattype_omschrijving_readonly_field(value)
            return res

        return super().render_readonly(field, result_repr, value)
