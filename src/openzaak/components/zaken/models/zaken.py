# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
import uuid
from datetime import date

from django.contrib.gis.db.models import GeometryField
from django.contrib.postgres.fields import ArrayField
from django.core.validators import RegexValidator
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from django_loose_fk.fields import FkOrURLField
from django_loose_fk.loaders import FetchError
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
from vng_api_common.models import APIMixin
from vng_api_common.utils import generate_unique_identification
from vng_api_common.validators import alphanumeric_excluding_diacritic

from openzaak.client import fetch_object
from openzaak.components.documenten.loaders import EIOLoader
from openzaak.utils.fields import DurationField
from openzaak.utils.mixins import AuditTrailMixin

from ..constants import AardZaakRelatie, BetalingsIndicatie, IndicatieMachtiging
from ..query import (
    ZaakBesluitQuerySet,
    ZaakInformatieObjectQuerySet,
    ZaakQuerySet,
    ZaakRelatedQuerySet,
)

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
]


class Zaak(AuditTrailMixin, APIMixin, models.Model):
    """
    Modelleer de structuur van een ZAAK.

    Een samenhangende hoeveelheid werk met een welgedefinieerde aanleiding
    en een welgedefinieerd eindresultaat, waarvan kwaliteit en doorlooptijd
    bewaakt moeten worden.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
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

    identificatie = models.CharField(
        max_length=40,
        blank=True,
        help_text="De unieke identificatie van de ZAAK binnen de organisatie "
        "die verantwoordelijk is voor de behandeling van de ZAAK.",
        validators=[alphanumeric_excluding_diacritic],
        db_index=True,
    )
    bronorganisatie = RSINField(
        help_text="Het RSIN van de Niet-natuurlijk persoon zijnde de "
        "organisatie die de zaak heeft gecreeerd. Dit moet een geldig "
        "RSIN zijn van 9 nummers en voldoen aan "
        "https://nl.wikipedia.org/wiki/Burgerservicenummer#11-proef"
    )
    omschrijving = models.CharField(
        max_length=80, blank=True, help_text="Een korte omschrijving van de zaak."
    )
    toelichting = models.TextField(
        max_length=1000, blank=True, help_text="Een toelichting op de zaak."
    )

    _zaaktype_url = models.URLField(
        _("extern zaaktype"),
        blank=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar extern ZAAKTYPE (in een andere Catalogi API)."
        ),
    )
    _zaaktype = models.ForeignKey(
        "catalogi.ZaakType",
        on_delete=models.CASCADE,
        help_text="URL-referentie naar het ZAAKTYPE (in de Catalogi API).",
        null=True,
        blank=True,
    )
    zaaktype = FkOrURLField(
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

    objects = ZaakQuerySet.as_manager()

    class Meta:
        verbose_name = "zaak"
        verbose_name_plural = "zaken"
        unique_together = ("bronorganisatie", "identificatie")

    def __str__(self):
        return self.identificatie

    def save(self, *args, **kwargs):
        if not self.identificatie:
            self.identificatie = generate_unique_identification(
                self, "registratiedatum"
            )

        if (
            self.betalingsindicatie == BetalingsIndicatie.nvt
            and self.laatste_betaaldatum
        ):
            self.laatste_betaaldatum = None

        super().save(*args, **kwargs)

    @property
    def current_status_uuid(self):
        status = self.status_set.first()
        return status.uuid if status else None

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

    _relevant_zaak_url = models.URLField(
        _("externe relevante zaak"),
        blank=True,
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
    url = FkOrURLField(
        fk_field="_relevant_zaak",
        url_field="_relevant_zaak_url",
        help_text=_("URL-referentie naar de ZAAK."),
    )

    aard_relatie = models.CharField(
        max_length=20,
        choices=AardZaakRelatie.choices,
        help_text=_(
            "Benamingen van de aard van de relaties van andere zaken tot (onderhanden) zaken."
        ),
    )


class Status(models.Model):
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

    _statustype_url = models.URLField(
        _("extern statustype"),
        blank=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar extern STATUSTYPE (in een andere Catalogi API)."
        ),
    )
    _statustype = models.ForeignKey(
        "catalogi.StatusType",
        on_delete=models.CASCADE,
        help_text="URL-referentie naar het STATUSTYPE (in de Catalogi API).",
        null=True,
        blank=True,
    )
    statustype = FkOrURLField(
        fk_field="_statustype",
        url_field="_statustype_url",
        help_text=_("URL-referentie naar het STATUSTYPE (in de Catalogi API)."),
    )

    # extra informatie
    datum_status_gezet = models.DateTimeField(
        help_text="De datum waarop de ZAAK de status heeft verkregen."
    )
    statustoelichting = models.TextField(
        max_length=1000,
        blank=True,
        help_text="Een, voor de initiator van de zaak relevante, toelichting "
        "op de status van een zaak.",
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "status"
        verbose_name_plural = "statussen"
        unique_together = ("zaak", "datum_status_gezet")

    def __str__(self):
        return "Status op {}".format(self.datum_status_gezet)

    def unique_representation(self):
        return f"({self.zaak.unique_representation()}) - {self.datum_status_gezet}"


class Resultaat(models.Model):
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

    _resultaattype_url = models.URLField(
        _("extern resultaattype"),
        blank=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar extern RESULTAATTYPE (in een andere Catalogi API)."
        ),
    )
    _resultaattype = models.ForeignKey(
        "catalogi.ResultaatType",
        on_delete=models.CASCADE,
        help_text="URL-referentie naar het RESULTAATTYPE (in de Catalogi API).",
        null=True,
        blank=True,
    )
    resultaattype = FkOrURLField(
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

    def __str__(self):
        return "Resultaat ({})".format(self.uuid)

    def unique_representation(self):
        return (
            f"({self.zaak.unique_representation()}) - {self.resultaattype.omschrijving}"
        )


class Rol(models.Model):
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

    _roltype_url = models.URLField(
        _("extern roltype"),
        blank=True,
        max_length=1000,
        help_text=_("URL-referentie naar extern ROLTYPE (in een andere Catalogi API)."),
    )
    _roltype = models.ForeignKey(
        "catalogi.RolType",
        on_delete=models.CASCADE,
        help_text="URL-referentie naar het ROLTYPE (in de Catalogi API).",
        null=True,
        blank=True,
    )
    roltype = FkOrURLField(
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
    roltoelichting = models.TextField(max_length=1000)

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

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Rollen"

    def save(self, *args, **kwargs):
        self._derive_roltype_attributes()

        super().save(*args, **kwargs)

    def _derive_roltype_attributes(self):
        if self.omschrijving and self.omschrijving_generiek:
            return

        self.omschrijving = self.roltype.omschrijving
        self.omschrijving_generiek = self.roltype.omschrijving_generiek

    def unique_representation(self):
        if self.betrokkene == "":
            return f"({self.zaak.unique_representation()}) - {self.roltoelichting}"

        betrokkene = (
            self.betrokkene.rstrip("/")
            if self.betrokkene.endswith("/")
            else self.betrokkene
        )
        return f"({self.zaak.unique_representation()}) - {betrokkene.rsplit('/')[-1]}"


class ZaakObject(models.Model):
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

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "zaakobject"
        verbose_name_plural = "zaakobjecten"

    def _get_object(self) -> dict:
        """
        Retrieve the `Object` specified as URL in `ZaakObject.object`.

        :return: A `dict` representing the object.
        """
        if not hasattr(self, "_object"):
            object_url = self.object
            self._object = None
            if object_url:
                self._object = fetch_object(self.object_type.lower(), url=object_url)
        return self._object

    def unique_representation(self):
        if self.object == "":
            return f"({self.zaak.unique_representation()}) - {self.relatieomschrijving}"

        object = self.object.rstrip("/") if self.object.endswith("/") else self.object
        return f"({self.zaak.unique_representation()}) - {object.rsplit('/')[-1]}"


class ZaakEigenschap(models.Model):
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
    _eigenschap_url = models.URLField(
        _("externe eigenschap"),
        blank=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar externe EIGENSCHAP (in een andere Catalogi API)."
        ),
    )
    _eigenschap = models.ForeignKey(
        "catalogi.Eigenschap",
        on_delete=models.CASCADE,
        help_text="URL-referentie naar de EIGENSCHAP (in de Catalogi API).",
        null=True,
        blank=True,
    )
    eigenschap = FkOrURLField(
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


class ZaakInformatieObject(models.Model):
    """
    Modelleer INFORMATIEOBJECTen die bij een ZAAK horen.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey(
        Zaak, on_delete=models.CASCADE, help_text=("URL-referentie naar de ZAAK.")
    )
    _informatieobject_url = models.URLField(
        _("External informatieobject"),
        blank=True,
        max_length=1000,
        help_text=_("URL to the informatieobject in an external API"),
    )
    _informatieobject = models.ForeignKey(
        "documenten.EnkelvoudigInformatieObjectCanonical",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="URL-referentie naar het INFORMATIEOBJECT (in de Documenten API), waar "
        "ook de relatieinformatie opgevraagd kan worden.",
    )
    informatieobject = FkOrURLField(
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
        help_text="URL of related IbjectInformatieObject object in the other API",
    )

    objects = ZaakInformatieObjectQuerySet.as_manager()

    class Meta:
        verbose_name = "zaakinformatieobject"
        verbose_name_plural = "zaakinformatieobjecten"
        unique_together = ("zaak", "_informatieobject")
        constraints = [
            models.UniqueConstraint(
                fields=["zaak", "_informatieobject_url"],
                condition=~models.Q(_informatieobject_url=""),
                name="unique_zaak_and_external_document",
            )
        ]

    def __str__(self) -> str:
        # In case of an external informatieobject, use the URL as fallback
        try:
            return f"{self.zaak} - {self.informatieobject}"
        except FetchError:
            return f"{self.zaak} - {self._informatieobject_url}"

    def unique_representation(self):
        zaak_repr = self.zaak.unique_representation()

        if hasattr(self.informatieobject, "identificatie"):
            doc_identificatie = self.informatieobject.identificatie
        else:
            doc_identificatie = self.informatieobject.latest_version.identificatie

        return f"({zaak_repr}) - {doc_identificatie}"

    def save(self, *args, **kwargs):
        # override to set aard_relatie
        self.aard_relatie = RelatieAarden.from_object_type("zaak")
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

    _besluit_url = models.URLField(
        _("extern besluit"),
        blank=True,
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
    besluit = FkOrURLField(
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
                fields=["zaak", "_besluit_url"],
                condition=~models.Q(_besluit_url=""),
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
