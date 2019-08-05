from django_filters import filters
from openzaak.components.zaken.models import (
    Resultaat, Rol, Status, Zaak, ZaakInformatieObject, ZaakObject
)
from vng_api_common.filtersets import FilterSet
from vng_api_common.utils import get_help_text


class ZaakFilter(FilterSet):
    class Meta:
        model = Zaak
        fields = {
            'identificatie': ['exact', ],
            'bronorganisatie': ['exact', ],
            'zaaktype': ['exact', ],
            'archiefnominatie': ['exact', 'in', ],
            'archiefactiedatum': ['exact', 'lt', 'gt', ],
            'archiefstatus': ['exact', 'in', ],
            'startdatum': ['exact', 'gt', 'gte', 'lt', 'lte']
        }


class RolFilter(FilterSet):
    betrokkene_identificatie__natuurlijk_persoon__inp_bsn = filters.CharFilter(
        field_name='natuurlijkpersoon__inp_bsn',
        help_text=get_help_text('zaken.NatuurlijkPersoon', 'inp_bsn')
    )
    betrokkene_identificatie__natuurlijk_persoon__anp_identificatie = filters.CharFilter(
        field_name='natuurlijkpersoon__anp_identificatie',
        help_text=get_help_text('zaken.NatuurlijkPersoon', 'anp_identificatie')
    )
    betrokkene_identificatie__natuurlijk_persoon__inp_a_nummer = filters.CharFilter(
        field_name='natuurlijkpersoon__inp_a_nummer',
        help_text=get_help_text('zaken.NatuurlijkPersoon', 'inp_a_nummer')
    )
    betrokkene_identificatie__niet_natuurlijk_persoon__inn_nnp_id = filters.CharFilter(
        field_name='nietnatuurlijkpersoon__inn_nnp_id',
        help_text=get_help_text('zaken.NietNatuurlijkPersoon', 'inn_nnp_id')
    )
    betrokkene_identificatie__niet_natuurlijk_persoon__ann_identificatie = filters.CharFilter(
        field_name='nietnatuurlijkpersoon__ann_identificatie',
        help_text=get_help_text('zaken.NietNatuurlijkPersoon', 'ann_identificatie')
    )
    betrokkene_identificatie__vestiging__vestigings_nummer = filters.CharFilter(
        field_name='vestiging__vestigings_nummer',
        help_text=get_help_text('zaken.Vestiging', 'vestigings_nummer')
    )
    betrokkene_identificatie__vestiging__identificatie = filters.CharFilter(
        field_name='organisatorischeeenheid__identificatie',
        help_text=get_help_text('zaken.OrganisatorischeEenheid', 'identificatie')
    )
    betrokkene_identificatie__medewerker__identificatie = filters.CharFilter(
        field_name='medewerker__identificatie',
        help_text=get_help_text('zaken.Medewerker', 'identificatie')
    )

    class Meta:
        model = Rol
        fields = (
            'zaak',
            'betrokkene',
            'betrokkene_type',
            'betrokkene_identificatie__natuurlijk_persoon__inp_bsn',
            'betrokkene_identificatie__natuurlijk_persoon__anp_identificatie',
            'betrokkene_identificatie__natuurlijk_persoon__inp_a_nummer',
            'betrokkene_identificatie__niet_natuurlijk_persoon__inn_nnp_id',
            'betrokkene_identificatie__niet_natuurlijk_persoon__ann_identificatie',
            'betrokkene_identificatie__vestiging__vestigings_nummer',
            'betrokkene_identificatie__vestiging__identificatie',
            'betrokkene_identificatie__medewerker__identificatie',
            'roltype',
            'omschrijving',
            'omschrijving_generiek',
        )


class StatusFilter(FilterSet):
    class Meta:
        model = Status
        fields = (
            'zaak',
            'statustype',
        )


class ResultaatFilter(FilterSet):
    class Meta:
        model = Resultaat
        fields = (
            'zaak',
            'resultaattype',
        )


class ZaakInformatieObjectFilter(FilterSet):
    class Meta:
        model = ZaakInformatieObject
        fields = (
            'zaak',
            'informatieobject',
        )


class ZaakObjectFilter(FilterSet):
    class Meta:
        model = ZaakObject
        fields = (
            'zaak',
            'object',
            'object_type',
        )
