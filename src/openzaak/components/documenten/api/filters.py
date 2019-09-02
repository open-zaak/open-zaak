from django_filters import rest_framework as filters
from vng_api_common.filters import URLModelChoiceFilter
from vng_api_common.filtersets import FilterSet
from vng_api_common.utils import get_help_text
from django.utils.translation import ugettext_lazy as _

from ..models import (
    EnkelvoudigInformatieObject,
    EnkelvoudigInformatieObjectCanonical,
    Gebruiksrechten,
    ObjectInformatieObject,
)
from openzaak.components.zaken.models import Zaak
from openzaak.components.besluiten.models import Besluit


class EnkelvoudigInformatieObjectListFilter(FilterSet):
    class Meta:
        model = EnkelvoudigInformatieObject
        fields = ("identificatie", "bronorganisatie")


class EnkelvoudigInformatieObjectDetailFilter(FilterSet):
    versie = filters.NumberFilter(field_name="versie")
    registratie_op = filters.IsoDateTimeFilter(
        field_name="begin_registratie", lookup_expr="lte", label="begin_registratie"
    )


class GebruiksrechtenFilter(FilterSet):
    informatieobject = URLModelChoiceFilter(
        queryset=EnkelvoudigInformatieObjectCanonical.objects.all(),
        instance_path="canonical",
        help_text=get_help_text("documenten.Gebruiksrechten", "informatieobject"),
    )

    class Meta:
        model = Gebruiksrechten
        fields = {
            "informatieobject": ["exact"],
            "startdatum": ["lt", "lte", "gt", "gte"],
            "einddatum": ["lt", "lte", "gt", "gte"],
        }


def object_queryset(request):
    object_value = request.query_params.get('object', '')
    if 'zaken' in object_value:
        return Zaak.objects.all()
    return Besluit.objects.all()


class ObjectFilter(URLModelChoiceFilter):
    def filter(self, qs, value):
        if isinstance(value, Zaak):
            self.field_name = 'zaak'
        else:
            self.field_name = 'besluit'

        return super().filter(qs, value)


class ObjectInformatieObjectFilter(FilterSet):
    informatieobject = URLModelChoiceFilter(
        queryset=EnkelvoudigInformatieObjectCanonical.objects.all(),
        instance_path="canonical",
        help_text=get_help_text(
            "documenten.ObjectInformatieObject", "informatieobject"
        ),
    )
    object = ObjectFilter(
        queryset=object_queryset,
        help_text=_(
            "URL-referentie naar het gerelateerde OBJECT (in deze of een andere API)."
        ),
    )

    class Meta:
        model = ObjectInformatieObject
        fields = (
            'object',
            "informatieobject",
        )
