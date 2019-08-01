from vng_api_common.filtersets import FilterSet

from openzaak.brc.datamodel.models import Besluit, BesluitInformatieObject


class BesluitFilter(FilterSet):
    class Meta:
        model = Besluit
        fields = (
            'identificatie',
            'verantwoordelijke_organisatie',
            'besluittype',
            'zaak',
        )

class BesluitInformatieObjectFilter(FilterSet):
    class Meta:
        model = BesluitInformatieObject
        fields = (
            'besluit',
            'informatieobject',
        )
