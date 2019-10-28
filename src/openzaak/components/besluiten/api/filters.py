from vng_api_common.filters import URLModelChoiceFilter
from vng_api_common.filtersets import FilterSet

from openzaak.components.documenten.models import EnkelvoudigInformatieObjectCanonical

from ..models import Besluit, BesluitInformatieObject


class BesluitFilter(FilterSet):
    class Meta:
        model = Besluit
        fields = (
            "identificatie",
            "verantwoordelijke_organisatie",
            "besluittype",
            "zaak",
        )


class BesluitInformatieObjectFilter(FilterSet):
    informatieobject = URLModelChoiceFilter(
        queryset=EnkelvoudigInformatieObjectCanonical.objects.all(),
        instance_path="canonical",
    )

    class Meta:
        model = BesluitInformatieObject
        fields = ("besluit", "informatieobject")
