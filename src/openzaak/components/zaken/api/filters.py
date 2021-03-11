# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from urllib.parse import urlparse

from django.conf import settings

from django_filters import filters
from django_loose_fk.filters import FkOrUrlFieldFilter
from django_loose_fk.utils import get_resource_for_path
from vng_api_common.filtersets import FilterSet
from vng_api_common.utils import get_help_text

from openzaak.utils.filters import MaximaleVertrouwelijkheidaanduidingFilter

from ..models import (
    KlantContact,
    Resultaat,
    Rol,
    Status,
    Zaak,
    ZaakInformatieObject,
    ZaakObject,
)


class ZaakFilter(FilterSet):
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
    )
    rol__betrokkene_identificatie__medewerker__identificatie = filters.CharFilter(
        field_name="rol__medewerker__identificatie",
        help_text=get_help_text("zaken.Medewerker", "identificatie"),
    )
    rol__betrokkene_identificatie__organisatorische_eenheid__identificatie = filters.CharFilter(
        field_name="rol__organisatorischeeenheid__identificatie",
        help_text=get_help_text("zaken.OrganisatorischeEenheid", "identificatie"),
    )

    class Meta:
        model = Zaak
        fields = {
            "identificatie": ["exact"],
            "bronorganisatie": ["exact"],
            "zaaktype": ["exact"],
            "archiefnominatie": ["exact", "in"],
            "archiefactiedatum": ["exact", "lt", "gt"],
            "archiefstatus": ["exact", "in"],
            "startdatum": ["exact", "gt", "gte", "lt", "lte"],
            # filters for werkvoorraad
            "rol__betrokkene_type": ["exact"],
            "rol__betrokkene": ["exact"],
            "rol__omschrijving_generiek": ["exact"],
        }


class RolFilter(FilterSet):
    betrokkene_identificatie__natuurlijk_persoon__inp_bsn = filters.CharFilter(
        field_name="natuurlijkpersoon__inp_bsn",
        help_text=get_help_text("zaken.NatuurlijkPersoon", "inp_bsn"),
    )
    betrokkene_identificatie__natuurlijk_persoon__anp_identificatie = filters.CharFilter(
        field_name="natuurlijkpersoon__anp_identificatie",
        help_text=get_help_text("zaken.NatuurlijkPersoon", "anp_identificatie"),
    )
    betrokkene_identificatie__natuurlijk_persoon__inp_a_nummer = filters.CharFilter(
        field_name="natuurlijkpersoon__inp_a_nummer",
        help_text=get_help_text("zaken.NatuurlijkPersoon", "inp_a_nummer"),
    )
    betrokkene_identificatie__niet_natuurlijk_persoon__inn_nnp_id = filters.CharFilter(
        field_name="nietnatuurlijkpersoon__inn_nnp_id",
        help_text=get_help_text("zaken.NietNatuurlijkPersoon", "inn_nnp_id"),
    )
    betrokkene_identificatie__niet_natuurlijk_persoon__ann_identificatie = filters.CharFilter(
        field_name="nietnatuurlijkpersoon__ann_identificatie",
        help_text=get_help_text("zaken.NietNatuurlijkPersoon", "ann_identificatie"),
    )
    betrokkene_identificatie__vestiging__vestigings_nummer = filters.CharFilter(
        field_name="vestiging__vestigings_nummer",
        help_text=get_help_text("zaken.Vestiging", "vestigings_nummer"),
    )
    betrokkene_identificatie__vestiging__identificatie = filters.CharFilter(
        field_name="organisatorischeeenheid__identificatie",
        help_text=get_help_text("zaken.OrganisatorischeEenheid", "identificatie"),
    )
    betrokkene_identificatie__medewerker__identificatie = filters.CharFilter(
        field_name="medewerker__identificatie",
        help_text=get_help_text("zaken.Medewerker", "identificatie"),
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
            "betrokkene_identificatie__vestiging__vestigings_nummer",
            "betrokkene_identificatie__vestiging__identificatie",
            "betrokkene_identificatie__medewerker__identificatie",
            "roltype",
            "omschrijving",
            "omschrijving_generiek",
        )


class StatusFilter(FilterSet):
    class Meta:
        model = Status
        fields = ("zaak", "statustype")


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

        local = parsed.netloc == host
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
