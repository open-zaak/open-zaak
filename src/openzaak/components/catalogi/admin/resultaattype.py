from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

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

    def get_extra_context(self, request, *args, **kwargs):
        context = super().get_extra_context(request, *args, **kwargs)
        self.zaaktype = context.get("zaaktype")
        return context

    def get_zaaktype_procestype(self, obj):
        try:
            url = obj.zaaktype.selectielijst_procestype
        except ZaakType.DoesNotExist:
            if self.zaaktype:
                url = self.zaaktype.selectielijst_procestype
            else:
                return _(
                    "Please save this Resultaattype first to get proper filtering of selectielijstklasses"
                )
        client = ReferentieLijstConfig.get_client()
        procestype = client.retrieve("procestype", url)
        return f"{procestype['nummer']} - {procestype['naam']}"

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
        (_("Archief"), {"fields": ("archiefnominatie", "archiefactietermijn")},),
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
    )
    raw_id_fields = ("zaaktype",)
    readonly_fields = ("get_zaaktype_procestype", "omschrijving_generiek")

    get_zaaktype_procestype.short_description = "zaaktype procestype"

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "selectielijstklasse":
            if self.zaaktype:
                kwargs["procestype"] = self.zaaktype.selectielijst_procestype
            elif request.resolver_match.kwargs.get("object_id"):
                obj = self.get_object(
                    request, request.resolver_match.kwargs.get("object_id")
                )
                kwargs["procestype"] = obj.zaaktype.selectielijst_procestype
            return get_selectielijstklasse_field(db_field, request, **kwargs)

        if db_field.name == "resultaattypeomschrijving":
            return get_resultaattype_omschrijving_field(db_field, request, **kwargs)

        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def render_readonly(self, field, result_repr, value):
        if not value:
            super().render_readonly(field, result_repr, value)

        if field.name == "selectielijstklasse":
            res = get_resultaat_readonly_field(value)
            return res

        if field.name == "resultaattypeomschrijving":
            res = get_resultaattype_omschrijving_readonly_field(value)
            return res

        return super().render_readonly(field, result_repr, value)
