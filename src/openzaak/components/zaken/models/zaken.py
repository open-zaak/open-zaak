# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
import logging
import uuid
from datetime import date
from typing import Optional
from uuid import UUID

from django.conf import settings
from django.contrib.gis.db.models import GeometryField
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import RegexValidator
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from django_loose_fk.loaders import FetchError
from vng_api_common.caching import ETagMixin
from vng_api_common.constants import (
    Archiefnominatie,
    Archiefstatus,
    RelatieAarden,
    RolOmschrijving,
    RolTypes,
    ZaakobjectTypes,
)
from vng_api_common.descriptors import GegevensGroepType
from vng_api_common.fields import RSINField, VertrouwelijkheidsAanduidingField
from zgw_consumers.models import ServiceUrlField

from openzaak.client import fetch_object
from openzaak.components.documenten.loaders import EIOLoader
from openzaak.components.zaken.validators import CorrectZaaktypeValidator
from openzaak.utils.fields import (
    DurationField,
    FkOrServiceUrlField,
    RelativeURLField,
    ServiceFkField,
)
from openzaak.utils.help_text import mark_experimental
from openzaak.utils.mixins import APIMixin, AuditTrailMixin

from ..constants import AardZaakRelatie, BetalingsIndicatie, IndicatieMachtiging
from ..query import (
    StatusQuerySet,
    ZaakBesluitQuerySet,
    ZaakInformatieObjectQuerySet,
    ZaakQuerySet,
    ZaakRelatedQuerySet,
)
from .identification import ZaakIdentificatie

logger = logging.getLogger(__name__)

__all__ = [
    "Zaak",
    "RelevanteZaakRelatie",
    "Status",
    "Resultaat",
    "Rol",
    "ZaakObject",
    "ZaakEigenschap",
    "ZaakKenmerk",
    "ZaakInformatieObject",
    "KlantContact",
    "ZaakBesluit",
    "ZaakContactMoment",
    "ZaakVerzoek",
]


class Zaak(ETagMixin, AuditTrailMixin, APIMixin, ZaakIdentificatie):
    """
    Modelleer de structuur van een ZAAK.

    Een samenhangende hoeveelheid werk met een welgedefinieerde aanleiding
    en een welgedefinieerd eindresultaat, waarvan kwaliteit en doorlooptijd
    bewaakt moeten worden.
    """

    # acts as the primary key - the (data) migrations ensure that the references
    # are correct
    identificatie_ptr = models.OneToOneField(
        ZaakIdentificatie,
        on_delete=models.PROTECT,
        parent_link=True,
        primary_key=True,
        verbose_name=_("Zaak identification details"),
        help_text=_(
            "Zaak identification details are tracked in a separate table so numbers "
            "can be generated/reserved before the zaak is actually created."
        ),
    )
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )

    # old fields, to be dropped in a future patch
    _id = models.IntegerField(db_column="id", null=True)
    _identificatie = models.CharField(
        db_column="identificatie",
        max_length=40,
        blank=True,
        help_text="De unieke identificatie van de ZAAK binnen de organisatie "
        "die verantwoordelijk is voor de behandeling van de ZAAK.",
        db_index=True,
    )
    _bronorganisatie = RSINField(
        db_column="bronorganisatie",
        help_text="Het RSIN van de Niet-natuurlijk persoon zijnde de "
        "organisatie die de zaak heeft gecreeerd. Dit moet een geldig "
        "RSIN zijn van 9 nummers en voldoen aan "
        "https://nl.wikipedia.org/wiki/Burgerservicenummer#11-proef",
    )

    # Relate 'is_deelzaak_van'
    # De relatie vanuit een zaak mag niet verwijzen naar
    # dezelfde zaak d.w.z. moet verwijzen naar een andere
    # zaak. Die andere zaak mag geen relatie ?is deelzaak
    # van? hebben (d.w.z. deelzaken van deelzaken worden
    # niet ondersteund).
    hoofdzaak = models.ForeignKey(
        "self",
        limit_choices_to={"hoofdzaak__isnull": True},
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="deelzaken",
        verbose_name="is deelzaak van",
        help_text=_(
            "URL-referentie naar de ZAAK, waarom verzocht is door de "
            "initiator daarvan, die behandeld wordt in twee of meer "
            "separate ZAAKen waarvan de onderhavige ZAAK er één is."
        ),
    )

    omschrijving = models.CharField(
        max_length=80, blank=True, help_text="Een korte omschrijving van de zaak."
    )
    toelichting = models.TextField(
        max_length=1000, blank=True, help_text="Een toelichting op de zaak."
    )

    _zaaktype_base_url = ServiceFkField(
        help_text="Basis deel van URL-referentie naar het extern ZAAKTYPE (in een andere Catalogi API).",
    )
    _zaaktype_relative_url = RelativeURLField(
        _("zaaktype relative url"),
        blank=True,
        null=True,
        help_text="Relatief deel van URL-referentie naar het extern ZAAKTYPE (in een andere Catalogi API).",
    )
    _zaaktype_url = ServiceUrlField(
        base_field="_zaaktype_base_url",
        relative_field="_zaaktype_relative_url",
        verbose_name=_("extern zaaktype"),
        null=True,
        blank=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar extern ZAAKTYPE (in een andere Catalogi API)."
        ),
    )
    _zaaktype = models.ForeignKey(
        "catalogi.ZaakType",
        on_delete=models.PROTECT,
        help_text="URL-referentie naar het ZAAKTYPE (in de Catalogi API).",
        null=True,
        blank=True,
    )
    zaaktype = FkOrServiceUrlField(
        fk_field="_zaaktype",
        url_field="_zaaktype_url",
        help_text="URL-referentie naar het ZAAKTYPE (in de Catalogi API).",
    )

    registratiedatum = models.DateField(
        help_text="De datum waarop de zaakbehandelende organisatie de ZAAK "
        "heeft geregistreerd. Indien deze niet opgegeven wordt, "
        "wordt de datum van vandaag gebruikt.",
        default=date.today,
    )
    verantwoordelijke_organisatie = RSINField(
        help_text="Het RSIN van de Niet-natuurlijk persoon zijnde de organisatie "
        "die eindverantwoordelijk is voor de behandeling van de "
        "zaak. Dit moet een geldig RSIN zijn van 9 nummers en voldoen aan "
        "https://nl.wikipedia.org/wiki/Burgerservicenummer#11-proef"
    )

    startdatum = models.DateField(
        help_text="De datum waarop met de uitvoering van de zaak is gestart",
        db_index=True,
    )
    einddatum = models.DateField(
        blank=True,
        null=True,
        help_text="De datum waarop de uitvoering van de zaak afgerond is.",
    )
    einddatum_gepland = models.DateField(
        blank=True,
        null=True,
        help_text="De datum waarop volgens de planning verwacht wordt dat de "
        "zaak afgerond wordt.",
    )
    uiterlijke_einddatum_afdoening = models.DateField(
        blank=True,
        null=True,
        help_text="De laatste datum waarop volgens wet- en regelgeving de zaak "
        "afgerond dient te zijn.",
    )
    publicatiedatum = models.DateField(
        _("publicatiedatum"),
        null=True,
        blank=True,
        help_text=_("Datum waarop (het starten van) de zaak gepubliceerd is of wordt."),
    )

    producten_of_diensten = ArrayField(
        models.URLField(_("URL naar product/dienst"), max_length=1000),
        default=list,
        help_text=_(
            "De producten en/of diensten die door de zaak worden voortgebracht. "
            "Dit zijn URLs naar de resources zoals die door de producten- "
            "en dienstencatalogus-API wordt ontsloten. "
            "De producten/diensten moeten bij het zaaktype vermeld zijn."
        ),
        blank=True,
    )

    communicatiekanaal = models.URLField(
        _("communicatiekanaal"),
        blank=True,
        max_length=1000,
        help_text=_(
            "Het medium waarlangs de aanleiding om een zaak te starten is ontvangen. "
            "URL naar een communicatiekanaal in de VNG-Referentielijst van communicatiekanalen."
        ),
    )

    vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduidingField(
        _("vertrouwlijkheidaanduiding"),
        help_text=_(
            "Aanduiding van de mate waarin het zaakdossier van de ZAAK voor de openbaarheid bestemd is."
        ),
    )

    betalingsindicatie = models.CharField(
        _("betalingsindicatie"),
        max_length=20,
        blank=True,
        choices=BetalingsIndicatie.choices,
        help_text=_(
            "Indicatie of de, met behandeling van de zaak gemoeide, "
            "kosten betaald zijn door de desbetreffende betrokkene."
        ),
    )
    laatste_betaaldatum = models.DateTimeField(
        _("laatste betaaldatum"),
        blank=True,
        null=True,
        help_text=_(
            "De datum waarop de meest recente betaling is verwerkt "
            "van kosten die gemoeid zijn met behandeling van de zaak."
        ),
    )

    zaakgeometrie = GeometryField(
        blank=True,
        null=True,
        help_text="Punt, lijn of (multi-)vlak geometrie-informatie.",
    )

    verlenging_reden = models.CharField(
        _("reden verlenging"),
        max_length=200,
        blank=True,
        help_text=_(
            "Omschrijving van de reden voor het verlengen van de behandeling van de zaak."
        ),
    )
    verlenging_duur = DurationField(
        _("duur verlenging"),
        blank=True,
        null=True,
        help_text=_(
            "Het aantal werkbare dagen waarmee de doorlooptijd van de "
            "behandeling van de ZAAK is verlengd (of verkort) ten opzichte "
            "van de eerder gecommuniceerde doorlooptijd."
        ),
    )
    verlenging = GegevensGroepType({"reden": verlenging_reden, "duur": verlenging_duur})

    opschorting_indicatie = models.BooleanField(
        _("indicatie opschorting"),
        default=False,
        blank=True,
        help_text=_(
            "Aanduiding of de behandeling van de ZAAK tijdelijk is opgeschort."
        ),
    )
    opschorting_reden = models.CharField(
        _("reden opschorting"),
        max_length=200,
        blank=True,
        help_text=_(
            "Omschrijving van de reden voor het opschorten van de behandeling van de zaak."
        ),
    )
    opschorting = GegevensGroepType(
        {"indicatie": opschorting_indicatie, "reden": opschorting_reden}
    )

    selectielijstklasse = models.URLField(
        _("selectielijstklasse"),
        blank=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar de categorie in de gehanteerde 'Selectielijst Archiefbescheiden' die, gezien "
            "het zaaktype en het resultaattype van de zaak, bepalend is voor het archiefregime van de zaak."
        ),
    )

    # Archiving
    archiefnominatie = models.CharField(
        _("archiefnominatie"),
        max_length=40,
        null=True,
        blank=True,
        choices=Archiefnominatie.choices,
        help_text=_(
            "Aanduiding of het zaakdossier blijvend bewaard of na een bepaalde termijn vernietigd moet worden."
        ),
        db_index=True,
    )
    archiefstatus = models.CharField(
        _("archiefstatus"),
        max_length=40,
        choices=Archiefstatus.choices,
        default=Archiefstatus.nog_te_archiveren,
        help_text=_(
            "Aanduiding of het zaakdossier blijvend bewaard of na een bepaalde termijn vernietigd moet worden."
        ),
        db_index=True,
    )
    archiefactiedatum = models.DateField(
        _("archiefactiedatum"),
        null=True,
        blank=True,
        help_text=_(
            "De datum waarop het gearchiveerde zaakdossier vernietigd moet worden dan wel overgebracht moet "
            "worden naar een archiefbewaarplaats. Wordt automatisch berekend bij het aanmaken of wijzigen van "
            "een RESULTAAT aan deze ZAAK indien nog leeg."
        ),
        db_index=True,
    )

    opdrachtgevende_organisatie = RSINField(
        help_text=_(
            "De krachtens publiekrecht ingestelde rechtspersoon dan wel "
            "ander niet-natuurlijk persoon waarbinnen het (bestuurs)orgaan zetelt "
            "dat opdracht heeft gegeven om taken uit te voeren waaraan de zaak "
            "invulling geeft."
        ),
        blank=True,
    )

    processobjectaard = models.CharField(
        _("procesobjectaard"),
        max_length=200,
        blank=True,
        help_text=_(
            "Omschrijving van het object, subject of gebeurtenis waarop, vanuit"
            " archiveringsoptiek, de zaak betrekking heeft."
        ),
    )

    startdatum_bewaartermijn = models.DateField(
        _("startdatum bewaartermijn"),
        null=True,
        blank=True,
        help_text=_(
            "De datum die de start markeert van de termijn waarop het zaakdossier"
            " vernietigd moet worden."
        ),
    )

    processobject_datumkenmerk = models.CharField(
        _("datumkenmerk"),
        max_length=250,
        blank=True,
        help_text=_(
            "De naam van de attribuutsoort van het procesobject dat bepalend is "
            "voor het einde van de procestermijn."
        ),
    )
    processobject_identificatie = models.CharField(
        _("identificatie"),
        max_length=250,
        blank=True,
        help_text=_("De unieke aanduiding van het procesobject."),
    )
    processobject_objecttype = models.CharField(
        _("objecttype"),
        max_length=250,
        blank=True,
        help_text=_("Het soort object dat het procesobject representeert."),
    )
    processobject_registratie = models.CharField(
        _("registratie"),
        max_length=250,
        blank=True,
        help_text=_(
            "De naam van de registratie waarvan het procesobject deel uit maakt."
        ),
    )
    communicatiekanaal_naam = models.CharField(
        _("communicatiekanaal naam"),
        max_length=250,
        blank=True,
        help_text=mark_experimental(
            _(
                "De naam van het medium waarlangs de aanleiding om een zaak te starten is ontvangen."
            )
        ),
    )
    processobject = GegevensGroepType(
        {
            "datumkenmerk": processobject_datumkenmerk,
            "identificatie": processobject_identificatie,
            "objecttype": processobject_objecttype,
            "registratie": processobject_registratie,
        },
    )

    created_on = models.DateTimeField(
        _("created on"),
        auto_now_add=True,
    )

    objects = ZaakQuerySet.as_manager()

    _current_status_uuid: Optional[UUID]

    class Meta:
        verbose_name = "zaak"
        verbose_name_plural = "zaken"

    def __str__(self):
        return self.identificatie

    def save(self, *args, **kwargs):
        if not self.identificatie:
            assert not self.identificatie_ptr_id
            self.identificatie_ptr = ZaakIdentificatie.objects.generate(
                organisation=self.bronorganisatie,
                date=self.registratiedatum,
            )
            self.identificatie = self.identificatie_ptr.identificatie
        elif not self.identificatie_ptr_id:

            reserved_identificatie = ZaakIdentificatie.objects.filter(
                identificatie=self.identificatie, bronorganisatie=self.bronorganisatie
            )
            if reserved_identificatie.exists():
                self.identificatie_ptr = reserved_identificatie.first()
            # else create one the normal way

        if (
            self.betalingsindicatie == BetalingsIndicatie.nvt
            and self.laatste_betaaldatum
        ):
            self.laatste_betaaldatum = None

        super().save(*args, **kwargs)

    @property
    def current_status_uuid(self):
        # .first() is used instead of .last because:
        #
        # * the viewset prefetches the statuses for each zaak and orders them
        #   descending on datum_status_gezet
        # * using .last() calls .reverse, which invalidates the prefetch cache.
        #
        # The Status.Meta is also set to order by descending datum_status_gezet so that
        # this code works correctly even when not doing prefetches.
        if hasattr(self, "_current_status_uuid"):
            return self._current_status_uuid
        status = self.status_set.first()
        return status.uuid if status else None

    @current_status_uuid.setter
    def current_status_uuid(self, value: Optional[UUID]):
        self._current_status_uuid = value

    @property
    def current_status(self):
        status = self.status_set.first()
        return status

    @property
    def is_closed(self) -> bool:
        return self.einddatum is not None

    def unique_representation(self):
        return f"{self.bronorganisatie} - {self.identificatie}"


class RelevanteZaakRelatie(models.Model):
    """
    Registreer een ZAAK als relevant voor een andere ZAAK
    """

    zaak = models.ForeignKey(
        Zaak, on_delete=models.CASCADE, related_name="relevante_andere_zaken"
    )

    _relevant_zaak_base_url = ServiceFkField(
        help_text="Basis deel van URL-referentie naar extern ZAAK (in een andere Zaken API).",
    )
    _relevant_zaak_relative_url = RelativeURLField(
        _("relevant zaak relative url"),
        blank=True,
        null=True,
        help_text="Relatief deel van URL-referentie naar extern ZAAK (in een andere Zaken API).",
    )
    _relevant_zaak_url = ServiceUrlField(
        base_field="_relevant_zaak_base_url",
        relative_field="_relevant_zaak_relative_url",
        verbose_name=_("externe relevante zaak"),
        blank=True,
        null=True,
        max_length=1000,
        help_text=_("URL-referentie naar extern ZAAK (in een andere zaken API)"),
    )
    _relevant_zaak = models.ForeignKey(
        Zaak,
        on_delete=models.CASCADE,
        verbose_name=_("relevante zaak"),
        help_text=_("URL-referentie naar de ZAAK."),
        null=True,
        blank=True,
    )
    url = FkOrServiceUrlField(
        fk_field="_relevant_zaak",
        url_field="_relevant_zaak_url",
        help_text=_(
            "URL-referentie naar de ZAAK. "
            "(Het ZAAKTYPE van deze ZAAK hoeft niet te zijn toegevoegd "
            "aan de gerelateerdeZaaktypen van het andere ZAAKTYPE.)"
        ),
    )

    aard_relatie = models.CharField(
        max_length=20,
        choices=AardZaakRelatie.choices,
        help_text=_(
            "Benamingen van de aard van de relaties van andere zaken tot (onderhanden) zaken."
        ),
    )

    overige_relatie = models.CharField(
        max_length=100,
        verbose_name=_("overige relatie"),
        blank=True,
        help_text=mark_experimental(
            "Naam van de overige relatie. Verplicht bij relatie aard `overig`."
        ),
    )

    toelichting = models.CharField(
        max_length=255,
        verbose_name=_("toelichting"),
        blank=True,
        help_text=mark_experimental(
            "Een toelichting op de aard van de relatie tussen beide ZAKEN. "
            "(vooral bedoeld in combinatie met relatie aard `overig`)"
        ),
    )


class Status(ETagMixin, APIMixin, models.Model):
    """
    Modelleer een status van een ZAAK.

    Een aanduiding van de stand van zaken van een ZAAK op basis van
    betekenisvol behaald resultaat voor de initiator van de ZAAK.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    # relaties
    zaak = models.ForeignKey(
        Zaak, on_delete=models.CASCADE, help_text=("URL-referentie naar de ZAAK.")
    )

    _statustype_base_url = ServiceFkField(
        help_text="Basis deel van URL-referentie naar extern STATUSTYPE (in een andere Catalogi API).",
    )
    _statustype_relative_url = RelativeURLField(
        _("statustype relative url"),
        blank=True,
        null=True,
        help_text="Relatief deel van URL-referentie naar extern STATUSTYPE (in een andere Catalogi API).",
    )
    _statustype_url = ServiceUrlField(
        base_field="_statustype_base_url",
        relative_field="_statustype_relative_url",
        verbose_name=_("extern statustype"),
        blank=True,
        null=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar extern STATUSTYPE (in een andere Catalogi API)."
        ),
    )
    _statustype = models.ForeignKey(
        "catalogi.StatusType",
        on_delete=models.PROTECT,
        help_text="URL-referentie naar het STATUSTYPE (in de Catalogi API).",
        null=True,
        blank=True,
    )
    statustype = FkOrServiceUrlField(
        fk_field="_statustype",
        url_field="_statustype_url",
        help_text=_("URL-referentie naar het STATUSTYPE (in de Catalogi API)."),
    )

    # extra informatie
    datum_status_gezet = models.DateTimeField(
        db_index=True, help_text="De datum waarop de ZAAK de status heeft verkregen."
    )
    statustoelichting = models.TextField(
        max_length=1000,
        blank=True,
        help_text="Een, voor de initiator van de zaak relevante, toelichting "
        "op de status van een zaak.",
    )
    gezetdoor = models.ForeignKey(
        "zaken.Rol",
        on_delete=models.CASCADE,
        verbose_name=_("gezet door"),
        related_name="statussen",
        blank=True,
        null=True,
        help_text=_(
            "De BETROKKENE die in zijn/haar ROL in een ZAAK heeft geregistreerd "
            "dat STATUSsen in die ZAAK bereikt zijn."
        ),
    )

    objects = StatusQuerySet.as_manager()

    class Meta:
        verbose_name = "status"
        verbose_name_plural = "statussen"
        unique_together = ("zaak", "datum_status_gezet")
        ordering = ("-datum_status_gezet",)  # most recent first

    def __str__(self):
        return "Status op {}".format(self.datum_status_gezet)

    def unique_representation(self):
        return f"({self.zaak.unique_representation()}) - {self.datum_status_gezet}"

    def full_clean(self, *args, **kwargs):
        super().full_clean(*args, **kwargs)
        CorrectZaaktypeValidator("statustype")(
            {
                "statustype": self.statustype,
                "zaak": self.zaak,
            }
        )

    @property
    def indicatie_laatst_gezette_status(self) -> bool:
        """⚡️ use annotated field when possible"""
        if hasattr(self, "max_datum_status_gezet"):
            return self.max_datum_status_gezet == self.datum_status_gezet

        return self.zaak.current_status_uuid == self.uuid


class Resultaat(ETagMixin, APIMixin, models.Model):
    """
    Het behaalde RESULTAAT is een koppeling tussen een RESULTAATTYPE en een
    ZAAK.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    # relaties
    zaak = models.OneToOneField(
        Zaak, on_delete=models.CASCADE, help_text=("URL-referentie naar de ZAAK.")
    )

    _resultaattype_base_url = ServiceFkField(
        help_text="Basis deel van URL-referentie naar extern RESULTAATTYPE (in een andere Catalogi API).",
    )
    _resultaattype_relative_url = RelativeURLField(
        _("resultaattype relative url"),
        blank=True,
        null=True,
        help_text="Relatief deel van URL-referentie naar extern RESULTAATTYPE (in een andere Catalogi API).",
    )
    _resultaattype_url = ServiceUrlField(
        base_field="_resultaattype_base_url",
        relative_field="_resultaattype_relative_url",
        verbose_name=_("extern resultaattype"),
        blank=True,
        null=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar extern RESULTAATTYPE (in een andere Catalogi API)."
        ),
    )
    _resultaattype = models.ForeignKey(
        "catalogi.ResultaatType",
        on_delete=models.PROTECT,
        help_text="URL-referentie naar het RESULTAATTYPE (in de Catalogi API).",
        null=True,
        blank=True,
    )
    resultaattype = FkOrServiceUrlField(
        fk_field="_resultaattype",
        url_field="_resultaattype_url",
        help_text=_("URL-referentie naar het RESULTAATTYPE (in de Catalogi API)."),
    )

    toelichting = models.TextField(
        max_length=1000,
        blank=True,
        help_text="Een toelichting op wat het resultaat van de zaak inhoudt.",
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "resultaat"
        verbose_name_plural = "resultaten"

    def full_clean(self, *args, **kwargs):
        super().full_clean(*args, **kwargs)
        CorrectZaaktypeValidator("resultaattype")(
            {
                "resultaattype": self.resultaattype,
                "zaak": self.zaak,
            }
        )

    def __str__(self):
        return "Resultaat ({})".format(self.uuid)

    def unique_representation(self):
        return (
            f"({self.zaak.unique_representation()}) - {self.resultaattype.omschrijving}"
        )


_SUPPORTS_AUTH_CONTEXT = models.Q(
    betrokkene_type__in=[
        RolTypes.natuurlijk_persoon,
        RolTypes.niet_natuurlijk_persoon,
        RolTypes.vestiging,
    ]
)


class Rol(ETagMixin, APIMixin, models.Model):
    """
    Modelleer de rol van een BETROKKENE bij een ZAAK.

    Een of meerdere BETROKKENEn hebben een of meerdere ROL(len) in een ZAAK.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey(
        Zaak, on_delete=models.CASCADE, help_text=("URL-referentie naar de ZAAK.")
    )
    betrokkene = models.URLField(
        help_text="URL-referentie naar een betrokkene gerelateerd aan de ZAAK.",
        max_length=1000,
        blank=True,
        db_index=True,
    )
    betrokkene_type = models.CharField(
        max_length=100,
        choices=RolTypes.choices,
        help_text="Type van de `betrokkene`.",
        db_index=True,
    )
    afwijkende_naam_betrokkene = models.TextField(
        _("afwijkende naam betrokkene"),
        help_text=_(
            "De naam van de betrokkene waaronder deze in relatie tot de zaak "
            "aangesproken wil worden."
        ),
        max_length=625,
        blank=True,
    )

    _roltype_base_url = ServiceFkField(
        help_text="Basis deel van URL-referentie naar extern ROLTYPE (in een andere Catalogi API).",
    )
    _roltype_relative_url = RelativeURLField(
        _("roltype relative url"),
        blank=True,
        null=True,
        help_text="Relatief deel van URL-referentie naar extern ROLTYPE (in een andere Catalogi API).",
    )
    _roltype_url = ServiceUrlField(
        base_field="_roltype_base_url",
        relative_field="_roltype_relative_url",
        verbose_name=_("extern roltype"),
        blank=True,
        null=True,
        max_length=1000,
        help_text=_("URL-referentie naar extern ROLTYPE (in een andere Catalogi API)."),
    )
    _roltype = models.ForeignKey(
        "catalogi.RolType",
        on_delete=models.PROTECT,
        help_text="URL-referentie naar het ROLTYPE (in de Catalogi API).",
        null=True,
        blank=True,
    )
    roltype = FkOrServiceUrlField(
        fk_field="_roltype",
        url_field="_roltype_url",
        help_text=_("URL-referentie naar een roltype binnen het ZAAKTYPE van de ZAAK."),
    )

    omschrijving = models.CharField(
        _("omschrijving"),
        max_length=100,
        editable=False,
        db_index=True,
        help_text=_(
            "Omschrijving van de aard van de ROL, afgeleid uit " "het ROLTYPE."
        ),
    )
    omschrijving_generiek = models.CharField(
        max_length=80,
        choices=RolOmschrijving.choices,
        help_text=_(
            "Algemeen gehanteerde benaming van de aard van de ROL, afgeleid uit het ROLTYPE."
        ),
        editable=False,
        db_index=True,
    )
    roltoelichting = models.TextField(
        max_length=1000,
        blank=True,
        help_text=mark_experimental(
            _(
                "Toelichting bij de rol (dit veld wijkt af van de standaard, omdat het veld niet verplicht is)."
            )
        ),
    )

    registratiedatum = models.DateTimeField(
        "registratiedatum",
        auto_now_add=True,
        help_text="De datum waarop dit object is geregistreerd.",
    )
    indicatie_machtiging = models.CharField(
        max_length=40,
        choices=IndicatieMachtiging.choices,
        blank=True,
        help_text="Indicatie machtiging",
    )

    contactpersoon_rol_emailadres = models.EmailField(
        _("email"),
        help_text=_(
            "Elektronich postadres waaronder de contactpersoon in de regel "
            "bereikbaar is."
        ),
        blank=True,
    )
    contactpersoon_rol_functie = models.CharField(
        _("functie"),
        help_text=_(
            "De aanduiding van de taken, rechten en plichten die de contactpersoon "
            "heeft binnen de organisatie van BETROKKENE. "
        ),
        max_length=50,
        blank=True,
    )
    contactpersoon_rol_telefoonnummer = models.CharField(
        _("telefoonnummer"),
        help_text=_(
            "Telefoonnummer waaronder de contactpersoon in de regel bereikbaar is."
        ),
        max_length=20,
        blank=True,
    )
    contactpersoon_rol_naam = models.CharField(
        _("naam"),
        help_text=_("De opgemaakte naam van de contactpersoon namens de BETROKKENE."),
        max_length=200,
        blank=True,
    )
    contactpersoon_rol = GegevensGroepType(
        {
            "emailadres": contactpersoon_rol_emailadres,
            "functie": contactpersoon_rol_functie,
            "telefoonnummer": contactpersoon_rol_telefoonnummer,
            "naam": contactpersoon_rol_naam,
        },
        optional=(
            "emailadres",
            "functie",
            "telefoonnummer",
        ),
    )

    authenticatie_context = models.JSONField(
        _("authentication context"),
        blank=True,
        null=True,
        encoder=DjangoJSONEncoder,
        help_text=_(
            "Metadata about the authentication context and mandate that applied when "
            "the role was added to the case."
        ),
    )

    objects = ZaakRelatedQuerySet.as_manager()

    #
    # EXPERIMENTAL ATTRIBUTES
    #
    begin_geldigheid = models.DateField(
        _("begindatum geldigheid"),
        null=True,
        blank=True,
        help_text=mark_experimental(
            _("De datum waarop de geldigheidsperiode van de ROL begint binnen de ZAAK.")
        ),
    )
    einde_geldigheid = models.DateField(
        _("einddatum geldigheid"),
        null=True,
        blank=True,
        help_text=mark_experimental(
            _(
                "De datum waarop de geldigheidsperiode van de ROL eindigt binnen de ZAAK."
            )
        ),
    )

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Rollen"
        constraints = [
            models.CheckConstraint(
                check=(
                    _SUPPORTS_AUTH_CONTEXT
                    | models.Q(
                        ~_SUPPORTS_AUTH_CONTEXT, authenticatie_context__isnull=True
                    )
                ),
                name="rol_auth_context_support_check",
            ),
        ]

    def save(self, *args, **kwargs):
        self._derive_roltype_attributes()

        super().save(*args, **kwargs)

    def full_clean(self, *args, **kwargs):
        super().full_clean(*args, **kwargs)
        CorrectZaaktypeValidator("roltype")(
            {
                "roltype": self.roltype,
                "zaak": self.zaak,
            }
        )

    def _derive_roltype_attributes(self):
        if self.omschrijving and self.omschrijving_generiek:
            return

        self.omschrijving = self.roltype.omschrijving
        self.omschrijving_generiek = self.roltype.omschrijving_generiek

    def unique_representation(self):
        if self.betrokkene == "":
            return f"({self.zaak.unique_representation()}) - {self.uuid}"

        betrokkene = (
            self.betrokkene.rstrip("/")
            if self.betrokkene.endswith("/")
            else self.betrokkene
        )
        return f"({self.zaak.unique_representation()}) - {betrokkene.rsplit('/')[-1]}"

    @cached_property
    def betrokkene_identificatie(self):
        """
        Return the details of the related betrokkene.

        Depending on the betrokkeneType, return the related object holding the
        ``betrokkeneIdentificatie`` details. This relation may not be set if a
        betrokkene URL is specified.
        """
        match self.betrokkene_type:
            case RolTypes.natuurlijk_persoon:
                return self.natuurlijkpersoon
            case RolTypes.niet_natuurlijk_persoon:
                return self.nietnatuurlijkpersoon
            case RolTypes.vestiging:
                return self.vestiging
            case RolTypes.organisatorische_eenheid:
                return self.organisatorischeeenheid
            case RolTypes.medewerker:
                return self.medewerker
            case _:
                raise ValueError("Unknown rol betrokkene type")

    def construct_auth_context_data(self) -> dict:
        """
        construct JSON which should be valid against auth context JSON schema
        https://github.com/maykinmedia/authentication-context-schemas/blob/main/schemas/schema.json
        """

        auth_context = self.authenticatie_context

        if not auth_context:
            return {}

        context = {
            "source": auth_context["source"],
            "levelOfAssurance": auth_context["level_of_assurance"],
        }
        if "mandate" in auth_context:
            context["mandate"] = auth_context["mandate"]

        if "representee" in auth_context:
            context["representee"] = {
                "identifierType": auth_context["representee"]["identifier_type"],
                "identifier": auth_context["representee"]["identifier"],
            }

        match self.betrokkene_type:
            # DigiD
            case RolTypes.natuurlijk_persoon:
                context["authorizee"] = {
                    "legalSubject": {
                        "identifierType": "bsn",
                        "identifier": self.natuurlijkpersoon.inp_bsn,
                    }
                }

            # eHerkenning
            case RolTypes.niet_natuurlijk_persoon:
                if self.nietnatuurlijkpersoon.kvk_nummer:
                    id_type = "kvkNummer"
                    id = self.nietnatuurlijkpersoon.kvk_nummer
                else:
                    id_type = "rsin"
                    id = self.nietnatuurlijkpersoon.inn_nnp_id

                context["authorizee"] = {
                    "legalSubject": {"identifierType": id_type, "identifier": id},
                    "actingSubject": {
                        "identifierType": "opaque",
                        "identifier": auth_context["acting_subject"],
                    },
                }

            case RolTypes.vestiging:
                context["authorizee"] = {
                    "legalSubject": {
                        "identifierType": "kvkNummer",
                        "identifier": self.vestiging.kvk_nummer,
                    },
                    "actingSubject": {
                        "identifierType": "opaque",
                        "identifier": auth_context["acting_subject"],
                    },
                }
                if self.vestiging.vestigings_nummer:
                    context["authorizee"]["legalSubject"][
                        "branchNumber"
                    ] = self.vestiging.vestigings_nummer

        return context


class ZaakObject(APIMixin, models.Model):
    """
    Modelleer een object behorende bij een ZAAK.

    Het OBJECT in kwestie kan in verschillende andere componenten leven,
    zoals het RSGB.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey(
        Zaak, on_delete=models.CASCADE, help_text=("URL-referentie naar de ZAAK.")
    )
    object = models.URLField(
        help_text="URL-referentie naar de resource die het OBJECT beschrijft.",
        max_length=1000,
        blank=True,
        db_index=True,
    )
    relatieomschrijving = models.CharField(
        max_length=80,
        blank=True,
        help_text="Omschrijving van de betrekking tussen de ZAAK en het OBJECT.",
    )
    object_type = models.CharField(
        max_length=100,
        choices=ZaakobjectTypes.choices,
        help_text="Beschrijft het type OBJECT gerelateerd aan de ZAAK. Als er "
        "geen passend type is, dan moet het type worden opgegeven "
        "onder `objectTypeOverige`.",
        db_index=True,
    )
    object_type_overige = models.CharField(
        max_length=100,
        blank=True,
        validators=[RegexValidator("[a-z_]+")],
        help_text="Beschrijft het type OBJECT als `objectType` de waarde "
        '"overige" heeft.',
    )
    object_type_overige_definitie = models.JSONField(
        _("definitie object type overige"),
        blank=True,
        null=True,
        help_text="Verwijzing naar het schema van het type OBJECT als `objectType` de "
        'waarde "overige" heeft.',
    )

    _zaakobjecttype_base_url = ServiceFkField(
        help_text="Basis deel van URL-referentie naar extern ZAAKOBJECTTYPE (in een andere Catalogi API).",
    )
    _zaakobjecttype_relative_url = RelativeURLField(
        _("zaakobjecttype relative url"),
        blank=True,
        null=True,
        help_text="Relatief deel van URL-referentie naar extern ZAAKOBJECTTYPE (in een andere Catalogi API).",
    )
    _zaakobjecttype_url = ServiceUrlField(
        base_field="_zaakobjecttype_base_url",
        relative_field="_zaakobjecttype_relative_url",
        verbose_name=_("extern zaakobjecttype"),
        blank=True,
        null=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar extern ZAAKOBJECTTYPE (in een andere Catalogi API)."
        ),
    )
    _zaakobjecttype = models.ForeignKey(
        "catalogi.ZaakObjectType",
        on_delete=models.PROTECT,
        help_text="URL-referentie naar het ZAAKOBJECTTYPE (in de lokale Catalogi API).",
        null=True,
        blank=True,
    )
    zaakobjecttype = FkOrServiceUrlField(
        fk_field="_zaakobjecttype",
        url_field="_zaakobjecttype_url",
        blank=True,
        null=True,
        help_text=_("URL-referentie naar het ZAAKOBJECTTYPE (in de Catalogi API)."),
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "zaakobject"
        verbose_name_plural = "zaakobjecten"

    def full_clean(self, *args, **kwargs):
        super().full_clean(*args, **kwargs)
        CorrectZaaktypeValidator("zaakobjecttype")(
            {
                "zaakobjecttype": self.zaakobjecttype,
                "zaak": self.zaak,
            }
        )

    def _get_object(self) -> dict:
        """
        Retrieve the `Object` specified as URL in `ZaakObject.object`.

        :return: A `dict` representing the object.
        """
        if not hasattr(self, "_object"):
            object_url = self.object
            self._object = None
            if object_url:
                self._object = fetch_object(url=object_url)
        return self._object

    def unique_representation(self):
        if self.object == "":
            return f"({self.zaak.unique_representation()}) - {self.relatieomschrijving}"

        object = self.object.rstrip("/") if self.object.endswith("/") else self.object
        return f"({self.zaak.unique_representation()}) - {object.rsplit('/')[-1]}"


class ZaakEigenschap(ETagMixin, APIMixin, models.Model):
    """
    Een relevant inhoudelijk gegeven waarvan waarden bij
    ZAAKen van eenzelfde ZAAKTYPE geregistreerd moeten
    kunnen worden en dat geen standaard kenmerk is van een
    ZAAK.

    Het RGBZ biedt generieke kenmerken van zaken. Bij zaken van een bepaald zaaktype kan de
    behoefte bestaan om waarden uit te wisselen van gegevens die specifiek zijn voor die zaken. Met
    dit groepattribuutsoort simuleren we de aanwezigheid van dergelijke eigenschappen. Aangezien
    deze eigenschappen specifiek zijn per zaaktype, modelleren we deze eigenschappen hier niet
    specifiek. De eigenschappen worden per zaaktype in een desbetreffende zaaktypecatalogus
    gespecificeerd.

    TODO: on save/submit, validate the value format against the defined eigenschap format
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey(Zaak, on_delete=models.CASCADE)

    _eigenschap_base_url = ServiceFkField(
        help_text="Basis deel van URL-referentie naar extern EIGENSCHAP (in een andere Catalogi API).",
    )
    _eigenschap_relative_url = RelativeURLField(
        _("eigenschap relative url"),
        blank=True,
        null=True,
        help_text="Relatief deel van URL-referentie naar extern EIGENSCHAP (in een andere Catalogi API).",
    )
    _eigenschap_url = ServiceUrlField(
        base_field="_eigenschap_base_url",
        relative_field="_eigenschap_relative_url",
        verbose_name=_("externe eigenschap"),
        blank=True,
        null=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar externe EIGENSCHAP (in een andere Catalogi API)."
        ),
    )
    _eigenschap = models.ForeignKey(
        "catalogi.Eigenschap",
        on_delete=models.PROTECT,
        help_text="URL-referentie naar de EIGENSCHAP (in de Catalogi API).",
        null=True,
        blank=True,
    )
    eigenschap = FkOrServiceUrlField(
        fk_field="_eigenschap",
        url_field="_eigenschap_url",
        help_text=_("URL-referentie naar de EIGENSCHAP (in de Catalogi API)."),
    )

    _naam = models.CharField(
        max_length=20,
        help_text=_("De naam van de EIGENSCHAP (overgenomen uit de Catalogi API)."),
    )
    waarde = models.TextField()

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "zaakeigenschap"
        verbose_name_plural = "zaakeigenschappen"

    def full_clean(self, *args, **kwargs):
        super().full_clean(*args, **kwargs)
        CorrectZaaktypeValidator("eigenschap")(
            {
                "eigenschap": self.eigenschap,
                "zaak": self.zaak,
            }
        )

    def __str__(self):
        return f"{self._naam}: {self.waarde}"

    def unique_representation(self):
        return f"({self.zaak.unique_representation()}) - {self._naam}"


class ZaakKenmerk(models.Model):
    """
    Model representatie van de Groepattribuutsoort 'Kenmerk'
    """

    zaak = models.ForeignKey(Zaak, on_delete=models.CASCADE)
    kenmerk = models.CharField(
        max_length=40,
        help_text="Identificeert uniek de zaak in een andere administratie.",
    )
    bron = models.CharField(
        max_length=40,
        help_text="De aanduiding van de administratie waar het kenmerk op " "slaat.",
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "zaak kenmerk"
        verbose_name_plural = "zaak kenmerken"

    def __str__(self) -> str:
        return self.unique_representation()

    def unique_representation(self):
        return f"({self.zaak.unique_representation()}) - {self.kenmerk}"


class ZaakInformatieObject(ETagMixin, APIMixin, models.Model):
    """
    Modelleer INFORMATIEOBJECTen die bij een ZAAK horen.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey(
        Zaak, on_delete=models.CASCADE, help_text=("URL-referentie naar de ZAAK.")
    )
    _informatieobject_base_url = ServiceFkField(
        help_text="Basis deel van URL-referentie naar de externe API",
    )
    _informatieobject_relative_url = RelativeURLField(
        _("informatieobject relative url"),
        blank=True,
        null=True,
        help_text="Relatief deel van URL-referentie naar de externe API",
    )
    _informatieobject_url = ServiceUrlField(
        base_field="_informatieobject_base_url",
        relative_field="_informatieobject_relative_url",
        verbose_name=_("External informatieobject"),
        blank=True,
        null=True,
        max_length=1000,
        help_text=_("URL to the informatieobject in an external API"),
    )
    _informatieobject = models.ForeignKey(
        "documenten.EnkelvoudigInformatieObjectCanonical",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        help_text="URL-referentie naar het INFORMATIEOBJECT (in de Documenten API), waar "
        "ook de relatieinformatie opgevraagd kan worden.",
    )
    informatieobject = FkOrServiceUrlField(
        fk_field="_informatieobject",
        url_field="_informatieobject_url",
        loader=EIOLoader(),
        help_text=_(
            "URL-referentie naar het INFORMATIEOBJECT (in de Documenten "
            "API), waar ook de relatieinformatie opgevraagd kan worden."
        ),
    )
    aard_relatie = models.CharField(
        "aard relatie", max_length=20, choices=RelatieAarden.choices
    )

    # relatiegegevens
    titel = models.CharField(
        "titel",
        max_length=200,
        blank=True,
        help_text="De naam waaronder het INFORMATIEOBJECT binnen het OBJECT bekend is.",
    )
    beschrijving = models.TextField(
        "beschrijving",
        blank=True,
        help_text="Een op het object gerichte beschrijving van de inhoud van"
        "het INFORMATIEOBJECT.",
    )
    registratiedatum = models.DateTimeField(
        "registratiedatum",
        auto_now_add=True,
        help_text="De datum waarop de behandelende organisatie het "
        "INFORMATIEOBJECT heeft geregistreerd bij het OBJECT. "
        "Geldige waardes zijn datumtijden gelegen op of voor de "
        "huidige datum en tijd.",
    )
    _objectinformatieobject_url = models.URLField(
        blank=True,
        max_length=1000,
        help_text="URL of related ObjectInformatieObject object in the other API",
    )
    vernietigingsdatum = models.DateTimeField(
        _("vernietigingsdatum"),
        help_text=_(
            "De datum waarop het informatieobject uit het zaakdossier verwijderd "
            "moet worden."
        ),
        null=True,
        blank=True,
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.CASCADE,
        verbose_name=_("status"),
        related_name="zaakinformatieobjecten",
        help_text=_(
            "De bij de desbetreffende ZAAK behorende STATUS waarvoor het "
            "ZAAK-INFORMATIEOBJECT relevant is (geweest) met het oog op het bereiken "
            "van die STATUS en/of de communicatie daarover."
        ),
        blank=True,
        null=True,
    )

    objects = ZaakInformatieObjectQuerySet.as_manager()

    class Meta:
        verbose_name = "zaakinformatieobject"
        verbose_name_plural = "zaakinformatieobjecten"
        unique_together = ("zaak", "_informatieobject")
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "zaak",
                    "_informatieobject_base_url",
                    "_informatieobject_relative_url",
                ],
                condition=~models.Q(_informatieobject_relative_url__isnull=True),
                name="unique_zaak_and_external_document",
            )
        ]

    def __str__(self) -> str:
        # Avoid making a query to the DMS for the representation
        if settings.CMIS_ENABLED:
            return f"{self.zaak} - {self._informatieobject_url}"

        # In case of an external informatieobject, use the URL as fallback
        try:
            return f"{self.zaak} - {self.informatieobject}"
        except FetchError:
            return f"{self.zaak} - {self._informatieobject_url}"

    def unique_representation(self):
        zaak_repr = self.zaak.unique_representation()

        informatieobject = self.informatieobject
        if hasattr(informatieobject, "identificatie"):
            doc_identificatie = informatieobject.identificatie
        else:
            doc_identificatie = informatieobject.latest_version.identificatie

        return f"({zaak_repr}) - {doc_identificatie}"

    def save(self, *args, **kwargs):
        # override to set aard_relatie
        self.aard_relatie = RelatieAarden.from_object_type("zaak")

        if (
            self._informatieobject is not None
            and self._informatieobject.latest_version is None
        ):
            raise ValidationError(
                "Related InformatieObject must have at least one version"
            )

        super().save(*args, **kwargs)


class KlantContact(models.Model):
    """
    Modelleer het contact tussen een medewerker en een klant.

    Een uniek en persoonlijk contact van een burger of bedrijfsmedewerker met
    een MEDEWERKER van de zaakbehandelende organisatie over een onderhanden of
    afgesloten ZAAK.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey(
        Zaak, on_delete=models.CASCADE, help_text=_("URL-referentie naar de ZAAK.")
    )
    identificatie = models.CharField(
        max_length=14,
        unique=True,
        help_text="De unieke aanduiding van een KLANTCONTACT",
    )
    datumtijd = models.DateTimeField(
        help_text="De datum en het tijdstip waarop het KLANTCONTACT begint"
    )
    kanaal = models.CharField(
        blank=True,
        max_length=20,
        help_text="Het communicatiekanaal waarlangs het KLANTCONTACT gevoerd wordt",
    )
    onderwerp = models.CharField(
        blank=True,
        max_length=200,
        help_text=_("Het onderwerp waarover contact is geweest met de klant."),
    )
    toelichting = models.CharField(
        blank=True,
        max_length=1000,
        help_text=_(
            "Een toelichting die inhoudelijk het contact met de klant beschrijft."
        ),
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "klantcontact"
        verbose_name_plural = "klantcontacten"

    def __str__(self):
        return self.identificatie

    def save(self, *args, **kwargs):
        if not self.identificatie:
            gen_id = True
            while gen_id:
                identificatie = get_random_string(length=12)
                gen_id = self.__class__.objects.filter(
                    identificatie=identificatie
                ).exists()
            self.identificatie = identificatie
        super().save(*args, **kwargs)

    def unique_representation(self):
        return f"{self.identificatie}"


class ZaakBesluit(models.Model):
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey(
        Zaak, on_delete=models.CASCADE, help_text=_("URL-referentie naar de ZAAK.")
    )

    _besluit_base_url = ServiceFkField(
        help_text="Basis deel van URL-referentie naar externe BESLUIT (in een andere Besluiten API).",
    )
    _besluit_relative_url = RelativeURLField(
        _("besluit relative url"),
        blank=True,
        null=True,
        help_text="Relatief deel van URL-referentie naar externe BESLUIT (in een andere Besluiten API).",
    )
    _besluit_url = ServiceUrlField(
        base_field="_besluit_base_url",
        relative_field="_besluit_relative_url",
        verbose_name=_("extern besluit"),
        blank=True,
        null=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar extern BESLUIT (in een andere Besluiten API)."
        ),
    )
    _besluit = models.ForeignKey(
        "besluiten.Besluit",
        on_delete=models.CASCADE,
        help_text="URL-referentie naar het BESLUIT (in de Besluiten API).",
        null=True,
        blank=True,
    )
    besluit = FkOrServiceUrlField(
        fk_field="_besluit",
        url_field="_besluit_url",
        help_text="URL-referentie naar het BESLUIT (in de Besluiten API).",
    )

    objects = ZaakBesluitQuerySet.as_manager()

    class Meta:
        verbose_name = _("zaakbesluit")
        verbose_name_plural = _("zaakbesluiten")
        unique_together = ("zaak", "_besluit")
        constraints = [
            models.UniqueConstraint(
                fields=["zaak", "_besluit_base_url", "_besluit_relative_url"],
                condition=models.Q(_besluit_base_url__isnull=False),
                name="unique_zaak_and_besluit",
            )
        ]

    def __str__(self):
        try:
            return _("Relation between {zaak} and {besluit}").format(
                zaak=self.zaak, besluit=self.besluit
            )
        except FetchError:
            return _("Relation between {zaak} and {besluit}").format(
                zaak=self.zaak, besluit=self._besluit_url
            )

    def unique_representation(self):
        zaak_repr = self.zaak.unique_representation()

        return f"({zaak_repr}) - {self.besluit.identificatie}"


class ZaakContactMoment(models.Model):
    """
    Model ContactMoment belonging to Zaak
    """

    uuid = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        help_text=_("Unieke resource identifier (UUID4)"),
    )
    zaak = models.ForeignKey(
        Zaak, on_delete=models.CASCADE, help_text=_("URL-referentie naar de ZAAK.")
    )
    contactmoment = models.URLField(
        "contactmoment",
        help_text=_("URL-referentie naar het CONTACTMOMENT (in de CMC API)"),
        max_length=1000,
    )
    _objectcontactmoment = models.URLField(
        "objectcontactmoment",
        blank=True,
        help_text="Link to the related object in the CMC API",
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "contactmoment"
        verbose_name_plural = "contactmomenten"
        unique_together = ("zaak", "contactmoment")

    def __str__(self) -> str:
        return self.unique_representation()

    def unique_representation(self):
        return f"({self.zaak.unique_representation()}) - {self.contactmoment}"


class ZaakVerzoek(models.Model):
    """
    Model Verzoek belonging to Zaak
    """

    uuid = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        help_text=_("Unieke resource identifier (UUID4)"),
    )
    zaak = models.ForeignKey(
        Zaak, on_delete=models.CASCADE, help_text=_("URL-referentie naar de ZAAK.")
    )
    verzoek = models.URLField(
        "verzoek",
        help_text=_("URL-referentie naar het VERZOEK (in de Klantinteractie API)"),
        max_length=1000,
    )
    _objectverzoek = models.URLField(
        "objectverzoek",
        blank=True,
        help_text="Link to the related object in the Klantinteractie API",
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "zaakverzoek"
        verbose_name_plural = "zaakverzoeken"
        unique_together = ("zaak", "verzoek")

    def __str__(self) -> str:
        return self.unique_representation()

    def unique_representation(self):
        return f"({self.zaak.unique_representation()}) - {self.verzoek}"
