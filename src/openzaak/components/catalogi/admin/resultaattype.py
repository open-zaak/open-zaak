from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from relativedeltafield import RelativeDeltaField

from openzaak.forms.fields import RelativeDeltaField as RelativeDeltaFormField

from ..models import ResultaatType
from .forms import ResultaatTypeForm


@admin.register(ResultaatType)
class ResultaatTypeAdmin(admin.ModelAdmin):
    model = ResultaatType
    form = ResultaatTypeForm

    # List
    list_display = (
        "omschrijving",
        "omschrijving_generiek",
        "selectielijstklasse",
        "uuid",
    )
    ordering = ("zaaktype", "omschrijving")
    search_fields = (
        "omschrijving",
        "omschrijving_generiek",
        "selectielijstklasse",
        "toelichting",
        "uuid",
    )

    # Details
    fieldsets = (
        (_("Algemeen"), {"fields": ("zaaktype", "omschrijving", "toelichting")}),
        (
            _("Gemeentelijke selectielijst"),
            {"fields": ("resultaattypeomschrijving", "selectielijstklasse")},
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
    )
    raw_id_fields = ("zaaktype",)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if isinstance(db_field, RelativeDeltaField):
            kwargs["form_class"] = RelativeDeltaFormField
        return super().formfield_for_dbfield(db_field, request, **kwargs)
