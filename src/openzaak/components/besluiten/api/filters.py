from django_loose_fk.filters import FkOrUrlFieldFilter
from vng_api_common.filtersets import FilterSet

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
    informatieobject = FkOrUrlFieldFilter(
        queryset=BesluitInformatieObject.objects.all(), instance_path="canonical"
    )

    class Meta:
        model = BesluitInformatieObject
        fields = ("besluit", "informatieobject")
