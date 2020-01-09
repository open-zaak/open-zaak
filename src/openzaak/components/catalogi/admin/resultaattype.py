from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from zds_client import Client

from openzaak.selectielijst.admin import (
    get_resultaattype_omschrijving_field,
    get_selectielijstklasse_field,
)
from openzaak.utils.admin import UUIDAdminMixin

from ..models import ResultaatType
from .forms import ResultaatTypeForm
from .mixins import CatalogusContextAdminMixin


@admin.register(ResultaatType)
class ResultaatTypeAdmin(UUIDAdminMixin, CatalogusContextAdminMixin, admin.ModelAdmin):
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

    def get_zaaktype_procestype(self, obj):
        url = obj.zaaktype.selectielijst_procestype
        client = Client("selectielijst")
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
            return get_selectielijstklasse_field(db_field, request, **kwargs)

        if db_field.name == "resultaattypeomschrijving":
            return get_resultaattype_omschrijving_field(db_field, request, **kwargs)

        return super().formfield_for_dbfield(db_field, request, **kwargs)
