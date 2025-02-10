# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from urllib.parse import urlparse

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_filters import filters
from django_loose_fk.filters import FkOrUrlFieldFilter
from django_loose_fk.utils import get_resource_for_path, is_local
from drf_spectacular.plumbing import build_choice_description_list
from vng_api_common.utils import get_field_attribute, get_help_text

from openzaak.components.zaken.api.serializers.zaken import ZaakSerializer
from openzaak.utils.filters import (
    ExpandFilter,
    MaximaleVertrouwelijkheidaanduidingFilter,
)
from openzaak.utils.filterset import FilterGroup, FilterSet, FilterSetWithGroups
from openzaak.utils.help_text import mark_experimental

from ..models import (
    KlantContact,
    Resultaat,
    Rol,
    Status,
    Zaak,
    ZaakContactMoment,
    ZaakInformatieObject,
    ZaakObject,
    ZaakVerzoek,
)
from .serializers.authentication_context import (
    DigiDLevelOfAssurance,
    eHerkenningLevelOfAssurance,
)

# custom filter to show cases for authorizee and representee
MACHTIGING_HELP_TEXT = mark_experimental(
    """filter objecten op basis van `indicatieMachtiging`:
* `eigen`: Toon objecten waarvan het attribuut `indicatieMachtiging` leeg is.
* `gemachtigde`: Toon objecten waarvan het attribuut `indicatieMachtiging` 'gemachtigde' is.
* `machtiginggever`: Toon objecten waarvan het attribuut `indicatieMachtiging` 'machtiginggever'
"""
)


class MachtigingChoices(models.TextChoices):
    eigen = "eigen", _("Eigen")
    gemachtigde = "gemachtigde", _("Gemachtigde")
    machtiginggever = "machtiginggever", _("Machtiginggever")


def machtiging_filter(queryset, name, value: str):
    if value == MachtigingChoices.eigen:
        return queryset.filter(**{name: ""})

    return queryset.filter(**{name: value})


class MaxLoAFilter(filters.ChoiceFilter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "choices",
            DigiDLevelOfAssurance.choices + eHerkenningLevelOfAssurance.choices,
        )
        kwargs.setdefault("lookup_expr", "lte")

        # add choice description
        help_text = kwargs.get("help_text", "")
        help_text += (
            "\n \n **Digid:** \n"
            + build_choice_description_list(DigiDLevelOfAssurance.choices)
            + "\n \n **eHerkenning:** \n"
            + build_choice_description_list(eHerkenningLevelOfAssurance.choices)
        )
        kwargs["help_text"] = help_text

        super().__init__(*args, **kwargs)

        # rewrite the field_name correctly
        self._field_name = self.field_name
        self.field_name = f"_{self._field_name}_order"

    def filter(self, qs, value):
        if value in filters.EMPTY_VALUES:
            return qs

        choices = (
            DigiDLevelOfAssurance
            if value in DigiDLevelOfAssurance
            else eHerkenningLevelOfAssurance
        )

        order_expression = choices.get_order_expression(self._field_name)
        numeric_value = choices.get_choice_order(value)

        qs = qs.annotate(**{self.field_name: order_expression})
        return super().filter(qs, numeric_value)


class ZaakFilter(FilterSetWithGroups):
    groups = [
        FilterGroup(
            [
                "rol__betrokkene_identificatie__natuurlijk_persoon__inp_bsn",
                "rol__betrokkene_identificatie__natuurlijk_persoon__anp_identificatie",
                "rol__betrokkene_identificatie__natuurlijk_persoon__inp_a_nummer",
                "rol__betrokkene_identificatie__niet_natuurlijk_persoon__inn_nnp_id",
                "rol__betrokkene_identificatie__niet_natuurlijk_persoon__ann_identificatie",
                "rol__betrokkene_identificatie__niet_natuurlijk_persoon__kvk_nummer",
                "rol__betrokkene_identificatie__vestiging__vestigings_nummer",
                "rol__betrokkene_identificatie__vestiging__kvk_nummer",
                "rol__betrokkene_identificatie__medewerker__identificatie",
                "rol__betrokkene_identificatie__organisatorische_eenheid__identificatie",
                "rol__machtiging",
                "rol__machtiging__loa",
                "rol__betrokkene_type",
                "rol__betrokkene",
                "rol__omschrijving_generiek",
            ]
        )
    ]

    identificatie__icontains = filters.CharFilter(
        field_name="identificatie",
        help_text=mark_experimental(
            "De unieke identificatie van de ZAAK "
            "(bevat de identificatie de gegeven waarden (hoofdletterongevoelig))"
        ),
        lookup_expr="icontains",
    )
    omschrijving = filters.CharFilter(
        help_text=mark_experimental(
            "Een korte omschrijving van de ZAAK "
            "(bevat de omschrijving de gegeven waarden (hoofdletterongevoelig))"
        ),
        lookup_expr="icontains",
    )
    zaaktype__omschrijving = filters.CharFilter(
        field_name="_zaaktype__zaaktype_omschrijving",
        help_text=mark_experimental(
            "Omschrijving van de aard van ZAAKen van het ZAAKTYPE"
            "(bevat de zaaktype omschrijving de gegeven waarden (hoofdletterongevoelig))"
        ),
        lookup_expr="icontains",
    )

    maximale_vertrouwelijkheidaanduiding = MaximaleVertrouwelijkheidaanduidingFilter(
        field_name="vertrouwelijkheidaanduiding",
        help_text=(
            "Zaken met een vertrouwelijkheidaanduiding die beperkter is dan de "
            "aangegeven aanduiding worden uit de resultaten gefiltered."
        ),
    )

    rol__betrokkene_identificatie__natuurlijk_persoon__inp_bsn = filters.CharFilter(
        field_name="rol__natuurlijkpersoon__inp_bsn",
        help_text=get_help_text("zaken.NatuurlijkPersoon", "inp_bsn"),
        max_length=get_field_attribute(
            "zaken.NatuurlijkPersoon", "inp_bsn", "max_length"
        ),
    )
    rol__betrokkene_identificatie__natuurlijk_persoon__anp_identificatie = (
        filters.CharFilter(
            field_name="rol__natuurlijkpersoon__anp_identificatie",
            help_text=get_help_text("zaken.NatuurlijkPersoon", "anp_identificatie"),
            max_length=get_field_attribute(
                "zaken.NatuurlijkPersoon", "anp_identificatie", "max_length"
            ),
        )
    )
    rol__betrokkene_identificatie__natuurlijk_persoon__inp_a_nummer = (
        filters.CharFilter(
            field_name="rol__natuurlijkpersoon__inp_a_nummer",
            help_text=get_help_text("zaken.NatuurlijkPersoon", "inp_a_nummer"),
            max_length=get_field_attribute(
                "zaken.NatuurlijkPersoon", "inp_a_nummer", "max_length"
            ),
        )
    )
    rol__betrokkene_identificatie__niet_natuurlijk_persoon__inn_nnp_id = (
        filters.CharFilter(
            field_name="rol__nietnatuurlijkpersoon__inn_nnp_id",
            help_text=get_help_text("zaken.NietNatuurlijkPersoon", "inn_nnp_id"),
        )
    )
    rol__betrokkene_identificatie__niet_natuurlijk_persoon__ann_identificatie = (
        filters.CharFilter(
            field_name="rol__nietnatuurlijkpersoon__ann_identificatie",
            help_text=get_help_text("zaken.NietNatuurlijkPersoon", "ann_identificatie"),
            max_length=get_field_attribute(
                "zaken.NietNatuurlijkPersoon", "ann_identificatie", "max_length"
            ),
        )
    )
    rol__betrokkene_identificatie__niet_natuurlijk_persoon__kvk_nummer = (
        filters.CharFilter(
            field_name="rol__nietnatuurlijkpersoon__kvk_nummer",
            help_text=get_help_text("zaken.NietNatuurlijkPersoon", "kvk_nummer"),
            max_length=get_field_attribute(
                "zaken.NietNatuurlijkPersoon", "kvk_nummer", "max_length"
            ),
        )
    )
    rol__betrokkene_identificatie__vestiging__vestigings_nummer = filters.CharFilter(
        field_name="rol__vestiging__vestigings_nummer",
        help_text=get_help_text("zaken.Vestiging", "vestigings_nummer"),
        max_length=get_field_attribute(
            "zaken.Vestiging", "vestigings_nummer", "max_length"
        ),
    )
    rol__betrokkene_identificatie__vestiging__kvk_nummer = filters.CharFilter(
        field_name="rol__vestiging__kvk_nummer",
        help_text=mark_experimental(get_help_text("zaken.Vestiging", "kvk_nummer")),
        max_length=get_field_attribute("zaken.Vestiging", "kvk_nummer", "max_length"),
    )
    rol__betrokkene_identificatie__medewerker__identificatie = filters.CharFilter(
        field_name="rol__medewerker__identificatie",
        help_text=get_help_text("zaken.Medewerker", "identificatie"),
        max_length=get_field_attribute(
            "zaken.Medewerker", "identificatie", "max_length"
        ),
    )
    rol__betrokkene_identificatie__organisatorische_eenheid__identificatie = (
        filters.CharFilter(
            field_name="rol__organisatorischeeenheid__identificatie",
            help_text=get_help_text("zaken.OrganisatorischeEenheid", "identificatie"),
        )
    )
    rol__machtiging = filters.ChoiceFilter(
        field_name="rol__indicatie_machtiging",
        method=machtiging_filter,
        help_text=MACHTIGING_HELP_TEXT,
        choices=MachtigingChoices.choices,
    )
    rol__machtiging__loa = MaxLoAFilter(
        field_name="rol__authenticatie_context__level_of_assurance",
        help_text=mark_experimental(
            "Enkel Zaken met een `rol.authenticatieContext.levelOfAssurance` die lager is dan of "
            "gelijk is aan de aangegeven aanduiding worden teruggeven als resultaten."
        ),
    )
    ordering = filters.OrderingFilter(
        fields=(
            "startdatum",
            "einddatum",
            "publicatiedatum",
            "archiefactiedatum",
            "registratiedatum",
            "identificatie",
        ),
        help_text=_("Het veld waarop de resultaten geordend worden."),
    )

    expand = ExpandFilter(serializer_class=ZaakSerializer)

    class Meta:
        model = Zaak
        fields = {
            "identificatie": ["exact"],
            "bronorganisatie": ["exact", "in"],
            "zaaktype": ["exact"],
            "archiefnominatie": ["exact", "in"],
            "archiefactiedatum": ["exact", "lt", "gt", "isnull"],
            "archiefstatus": ["exact", "in"],
            "startdatum": ["exact", "gt", "gte", "lt", "lte"],
            "registratiedatum": ["exact", "gt", "lt"],
            "einddatum": ["exact", "gt", "lt", "isnull"],
            "einddatum_gepland": ["exact", "gt", "lt"],
            "uiterlijke_einddatum_afdoening": ["exact", "gt", "lt"],
            # filters for werkvoorraad
            "rol__betrokkene_type": ["exact"],
            "rol__betrokkene": ["exact"],
            "rol__omschrijving_generiek": ["exact"],
        }


class ZaakDetailFilter(FilterSet):
    expand = ExpandFilter(serializer_class=ZaakSerializer)


class RolFilter(FilterSet):
    betrokkene_identificatie__natuurlijk_persoon__inp_bsn = filters.CharFilter(
        field_name="natuurlijkpersoon__inp_bsn",
        help_text=get_help_text("zaken.NatuurlijkPersoon", "inp_bsn"),
    )
    betrokkene_identificatie__natuurlijk_persoon__anp_identificatie = (
        filters.CharFilter(
            field_name="natuurlijkpersoon__anp_identificatie",
            help_text=get_help_text("zaken.NatuurlijkPersoon", "anp_identificatie"),
        )
    )
    betrokkene_identificatie__natuurlijk_persoon__inp_a_nummer = filters.CharFilter(
        field_name="natuurlijkpersoon__inp_a_nummer",
        help_text=get_help_text("zaken.NatuurlijkPersoon", "inp_a_nummer"),
    )
    betrokkene_identificatie__niet_natuurlijk_persoon__inn_nnp_id = filters.CharFilter(
        field_name="nietnatuurlijkpersoon__inn_nnp_id",
        help_text=get_help_text("zaken.NietNatuurlijkPersoon", "inn_nnp_id"),
    )
    betrokkene_identificatie__niet_natuurlijk_persoon__ann_identificatie = (
        filters.CharFilter(
            field_name="nietnatuurlijkpersoon__ann_identificatie",
            help_text=get_help_text("zaken.NietNatuurlijkPersoon", "ann_identificatie"),
        )
    )
    betrokkene_identificatie__niet_natuurlijk_persoon__kvk_nummer = filters.CharFilter(
        field_name="nietnatuurlijkpersoon__kvk_nummer",
        help_text=get_help_text("zaken.NietNatuurlijkPersoon", "kvk_nummer"),
    )
    betrokkene_identificatie__vestiging__vestigings_nummer = filters.CharFilter(
        field_name="vestiging__vestigings_nummer",
        help_text=get_help_text("zaken.Vestiging", "vestigings_nummer"),
    )
    betrokkene_identificatie__vestiging__kvk_nummer = filters.CharFilter(
        field_name="vestiging__kvk_nummer",
        help_text=mark_experimental(get_help_text("zaken.Vestiging", "kvk_nummer")),
    )
    betrokkene_identificatie__organisatorische_eenheid__identificatie = (
        filters.CharFilter(
            field_name="organisatorischeeenheid__identificatie",
            help_text=get_help_text("zaken.OrganisatorischeEenheid", "identificatie"),
        )
    )
    betrokkene_identificatie__medewerker__identificatie = filters.CharFilter(
        field_name="medewerker__identificatie",
        help_text=get_help_text("zaken.Medewerker", "identificatie"),
    )
    machtiging = filters.ChoiceFilter(
        field_name="indicatie_machtiging",
        method=machtiging_filter,
        help_text=MACHTIGING_HELP_TEXT,
        choices=MachtigingChoices.choices,
    )
    machtiging__loa = MaxLoAFilter(
        field_name="authenticatie_context__level_of_assurance",
        help_text=mark_experimental(
            "Rollen met een 'authenticatieContext.levelOfAssurance' die lager of gelijk is dan de "
            "aangegeven aanduiding worden teruggeven als resultaten."
        ),
    )

    class Meta:
        model = Rol
        fields = (
            "zaak",
            "betrokkene",
            "betrokkene_type",
            "betrokkene_identificatie__natuurlijk_persoon__inp_bsn",
            "betrokkene_identificatie__natuurlijk_persoon__anp_identificatie",
            "betrokkene_identificatie__natuurlijk_persoon__inp_a_nummer",
            "betrokkene_identificatie__niet_natuurlijk_persoon__inn_nnp_id",
            "betrokkene_identificatie__niet_natuurlijk_persoon__ann_identificatie",
            "betrokkene_identificatie__niet_natuurlijk_persoon__kvk_nummer",
            "betrokkene_identificatie__vestiging__vestigings_nummer",
            "betrokkene_identificatie__vestiging__kvk_nummer",
            "betrokkene_identificatie__organisatorische_eenheid__identificatie",
            "betrokkene_identificatie__medewerker__identificatie",
            "roltype",
            "omschrijving",
            "omschrijving_generiek",
            "machtiging",
            "machtiging__loa",
        )


class StatusFilter(FilterSet):
    indicatie_laatst_gezette_status = filters.BooleanFilter(
        method="filter_is_last_status",
        help_text=_(
            "Het gegeven is afleidbaar uit de historie van de attribuutsoort Datum "
            "status gezet van van alle statussen bij de desbetreffende zaak."
        ),
    )

    class Meta:
        model = Status
        fields = ("zaak", "statustype", "indicatie_laatst_gezette_status")

    def filter_is_last_status(self, queryset, name, value):
        if value is True:
            return queryset.filter(
                datum_status_gezet=models.F("max_datum_status_gezet")
            )

        if value is False:
            return queryset.exclude(
                datum_status_gezet=models.F("max_datum_status_gezet")
            )

        return queryset.none()


class ResultaatFilter(FilterSet):
    class Meta:
        model = Resultaat
        fields = ("zaak", "resultaattype")


class FkOrUrlOrCMISFieldFilter(FkOrUrlFieldFilter):
    def filter(self, qs, value):
        if not value:
            return qs

        parsed = urlparse(value)
        host = self.parent.request.get_host()

        local = is_local(host, value)
        if settings.CMIS_ENABLED:
            local = False

        # introspect field to build filter
        model_field = self.model._meta.get_field(self.field_name)

        if local:
            local_object = get_resource_for_path(parsed.path)
            if self.instance_path:
                for bit in self.instance_path.split("."):
                    local_object = getattr(local_object, bit)
            filters = {f"{model_field.fk_field}__{self.lookup_expr}": local_object}
        else:
            filters = {f"{model_field.url_field}__{self.lookup_expr}": value}

        qs = self.get_method(qs)(**filters)
        return qs.distinct() if self.distinct else qs


class ZaakInformatieObjectFilter(FilterSet):
    informatieobject = FkOrUrlOrCMISFieldFilter(
        queryset=ZaakInformatieObject.objects.all(),
        instance_path="canonical",
        help_text=get_help_text("zaken.ZaakInformatieObject", "informatieobject"),
    )

    class Meta:
        model = ZaakInformatieObject
        fields = ("zaak", "informatieobject")


class ZaakObjectFilter(FilterSet):
    class Meta:
        model = ZaakObject
        fields = ("zaak", "object", "object_type")


class KlantContactFilter(FilterSet):
    class Meta:
        model = KlantContact
        fields = ("zaak",)


class ZaakContactMomentFilter(FilterSet):
    class Meta:
        model = ZaakContactMoment
        fields = ("zaak", "contactmoment")


class ZaakVerzoekFilter(FilterSet):
    class Meta:
        model = ZaakVerzoek
        fields = ("zaak", "verzoek")
