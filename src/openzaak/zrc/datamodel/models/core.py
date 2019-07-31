import logging
import uuid
from datetime import date

from django.conf import settings
from django.contrib.gis.db.models import GeometryField
from django.contrib.postgres.fields import ArrayField
from django.core.validators import RegexValidator
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _

from vng_api_common.constants import (
    Archiefnominatie, Archiefstatus, RelatieAarden, RolOmschrijving, RolTypes,
    ZaakobjectTypes
)
from vng_api_common.descriptors import GegevensGroepType
from vng_api_common.fields import (
    DaysDurationField, RSINField, VertrouwelijkheidsAanduidingField
)
from vng_api_common.models import APICredential, APIMixin
from vng_api_common.utils import (
    generate_unique_identification, request_object_attribute
)
from vng_api_common.validators import alphanumeric_excluding_diacritic

from ..constants import (
    AardZaakRelatie, BetalingsIndicatie, IndicatieMachtiging
)
from ..query import ZaakQuerySet, ZaakRelatedQuerySet

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


class Zaak(APIMixin, models.Model):
    """
    Modelleer de structuur van een ZAAK.

    Een samenhangende hoeveelheid werk met een welgedefinieerde aanleiding
    en een welgedefinieerd eindresultaat, waarvan kwaliteit en doorlooptijd
    bewaakt moeten worden.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )

    # Relate 'is_deelzaak_van'
    # De relatie vanuit een zaak mag niet verwijzen naar
    # dezelfde zaak d.w.z. moet verwijzen naar een andere
    # zaak. Die andere zaak mag geen relatie ?is deelzaak
    # van? hebben (d.w.z. deelzaken van deelzaken worden
    # niet ondersteund).
    hoofdzaak = models.ForeignKey(
        'self', limit_choices_to={'hoofdzaak__isnull': True},
        null=True, blank=True, on_delete=models.CASCADE,
        related_name='deelzaken', verbose_name='is deelzaak van',
        help_text=_("URL-referentie naar de ZAAK, waarom verzocht is door de "
                    "initiator daarvan, die behandeld wordt in twee of meer "
                    "separate ZAAKen waarvan de onderhavige ZAAK er één is.")
    )

    identificatie = models.CharField(
        max_length=40, blank=True,
        help_text='De unieke identificatie van de ZAAK binnen de organisatie '
                  'die verantwoordelijk is voor de behandeling van de ZAAK.',
        validators=[alphanumeric_excluding_diacritic]
    )
    bronorganisatie = RSINField(
        help_text='Het RSIN van de Niet-natuurlijk persoon zijnde de '
                  'organisatie die de zaak heeft gecreeerd. Dit moet een geldig '
                  'RSIN zijn van 9 nummers en voldoen aan '
                  'https://nl.wikipedia.org/wiki/Burgerservicenummer#11-proef'
    )
    omschrijving = models.CharField(
        max_length=80, blank=True,
        help_text='Een korte omschrijving van de zaak.')
    toelichting = models.TextField(
        max_length=1000, blank=True,
        help_text='Een toelichting op de zaak.'
    )
    zaaktype = models.URLField(
        _("zaaktype"),
        help_text="URL-referentie naar het ZAAKTYPE (in de Catalogi API) in de CATALOGUS waar deze voorkomt",
        max_length=1000
    )
    registratiedatum = models.DateField(
        help_text='De datum waarop de zaakbehandelende organisatie de ZAAK '
                  'heeft geregistreerd. Indien deze niet opgegeven wordt, '
                  'wordt de datum van vandaag gebruikt.',
        default=date.today
    )
    verantwoordelijke_organisatie = RSINField(
        help_text='Het RSIN van de Niet-natuurlijk persoon zijnde de organisatie '
                  'die eindverantwoordelijk is voor de behandeling van de '
                  'zaak. Dit moet een geldig RSIN zijn van 9 nummers en voldoen aan '
                  'https://nl.wikipedia.org/wiki/Burgerservicenummer#11-proef'
    )

    startdatum = models.DateField(
        help_text='De datum waarop met de uitvoering van de zaak is gestart')
    einddatum = models.DateField(
        blank=True, null=True,
        help_text='De datum waarop de uitvoering van de zaak afgerond is.',
    )
    einddatum_gepland = models.DateField(
        blank=True, null=True,
        help_text='De datum waarop volgens de planning verwacht wordt dat de '
                  'zaak afgerond wordt.',
    )
    uiterlijke_einddatum_afdoening = models.DateField(
        blank=True, null=True,
        help_text='De laatste datum waarop volgens wet- en regelgeving de zaak '
                  'afgerond dient te zijn.'
    )
    publicatiedatum = models.DateField(
        _("publicatiedatum"), null=True, blank=True,
        help_text=_("Datum waarop (het starten van) de zaak gepubliceerd is of wordt.")
    )

    producten_of_diensten = ArrayField(
        models.URLField(_("URL naar product/dienst"), max_length=1000), default=list,
        help_text=_("De producten en/of diensten die door de zaak worden voortgebracht. "
                    "Dit zijn URLs naar de resources zoals die door de producten- "
                    "en dienstencatalogus-API wordt ontsloten. "
                    "De producten/diensten moeten bij het zaaktype vermeld zijn."),
        blank=True,
    )

    communicatiekanaal = models.URLField(
        _("communicatiekanaal"), blank=True, max_length=1000,
        help_text=_("Het medium waarlangs de aanleiding om een zaak te starten is ontvangen. "
                    "URL naar een communicatiekanaal in de VNG-Referentielijst van communicatiekanalen.")
    )

    vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduidingField(
        _("vertrouwlijkheidaanduiding"),
        help_text=_("Aanduiding van de mate waarin het zaakdossier van de ZAAK voor de openbaarheid bestemd is.")
    )

    betalingsindicatie = models.CharField(
        _("betalingsindicatie"), max_length=20, blank=True,
        choices=BetalingsIndicatie.choices,
        help_text=_("Indicatie of de, met behandeling van de zaak gemoeide, "
                    "kosten betaald zijn door de desbetreffende betrokkene.")
    )
    laatste_betaaldatum = models.DateTimeField(
        _("laatste betaaldatum"), blank=True, null=True,
        help_text=_("De datum waarop de meest recente betaling is verwerkt "
                    "van kosten die gemoeid zijn met behandeling van de zaak.")
    )

    zaakgeometrie = GeometryField(
        blank=True, null=True,
        help_text="Punt, lijn of (multi-)vlak geometrie-informatie."
    )

    verlenging_reden = models.CharField(
        _("reden verlenging"), max_length=200, blank=True,
        help_text=_("Omschrijving van de reden voor het verlengen van de behandeling van de zaak.")
    )
    verlenging_duur = DaysDurationField(
        _("duur verlenging"), blank=True, null=True,
        help_text=_("Het aantal werkbare dagen waarmee de doorlooptijd van de "
                    "behandeling van de ZAAK is verlengd (of verkort) ten opzichte "
                    "van de eerder gecommuniceerde doorlooptijd.")
    )
    verlenging = GegevensGroepType({
        'reden': verlenging_reden,
        'duur': verlenging_duur,
    })

    opschorting_indicatie = models.BooleanField(
        _("indicatie opschorting"), default=False, blank=True,
        help_text=_("Aanduiding of de behandeling van de ZAAK tijdelijk is opgeschort.")
    )
    opschorting_reden = models.CharField(
        _("reden opschorting"), max_length=200, blank=True,
        help_text=_("Omschrijving van de reden voor het opschorten van de behandeling van de zaak.")
    )
    opschorting = GegevensGroepType({
        'indicatie': opschorting_indicatie,
        'reden': opschorting_reden,
    })

    selectielijstklasse = models.URLField(
        _("selectielijstklasse"), blank=True, max_length=1000,
        help_text=_("URL-referentie naar de categorie in de gehanteerde 'Selectielijst Archiefbescheiden' die, gezien "
                    "het zaaktype en het resultaattype van de zaak, bepalend is voor het archiefregime van de zaak.")
    )

    # Archiving
    archiefnominatie = models.CharField(
        _("archiefnominatie"), max_length=40, null=True, blank=True,
        choices=Archiefnominatie.choices,
        help_text=_("Aanduiding of het zaakdossier blijvend bewaard of na een bepaalde termijn vernietigd moet worden.")
    )
    archiefstatus = models.CharField(
        _("archiefstatus"), max_length=40,
        choices=Archiefstatus.choices, default=Archiefstatus.nog_te_archiveren,
        help_text=_("Aanduiding of het zaakdossier blijvend bewaard of na een bepaalde termijn vernietigd moet worden.")
    )
    archiefactiedatum = models.DateField(
        _("archiefactiedatum"), null=True, blank=True,
        help_text=_("De datum waarop het gearchiveerde zaakdossier vernietigd moet worden dan wel overgebracht moet "
                    "worden naar een archiefbewaarplaats. Wordt automatisch berekend bij het aanmaken of wijzigen van "
                    "een RESULTAAT aan deze ZAAK indien nog leeg.")
    )

    objects = ZaakQuerySet.as_manager()

    class Meta:
        verbose_name = 'zaak'
        verbose_name_plural = 'zaken'
        unique_together = ('bronorganisatie', 'identificatie')

    def __str__(self):
        return self.identificatie

    def save(self, *args, **kwargs):
        if not self.identificatie:
            self.identificatie = generate_unique_identification(self, 'registratiedatum')

        if self.betalingsindicatie == BetalingsIndicatie.nvt and self.laatste_betaaldatum:
            self.laatste_betaaldatum = None

        super().save(*args, **kwargs)

    @property
    def current_status_uuid(self):
        status = self.status_set.order_by('-datum_status_gezet').first()
        return status.uuid if status else None

    def unique_representation(self):
        return f"{self.bronorganisatie} - {self.identificatie}"


class RelevanteZaakRelatie(models.Model):
    """
    Registreer een ZAAK als relevant voor een andere ZAAK
    """
    zaak = models.ForeignKey(
        'Zaak', on_delete=models.CASCADE, related_name='relevante_andere_zaken',
    )
    url = models.URLField(_("URL-referentie naar de ZAAK."), max_length=1000)
    aard_relatie = models.CharField(
        max_length=20, choices=AardZaakRelatie.choices,
        help_text=_('Benamingen van de aard van de relaties van andere zaken tot (onderhanden) zaken.')
    )


class Status(models.Model):
    """
    Modelleer een status van een ZAAK.

    Een aanduiding van de stand van zaken van een ZAAK op basis van
    betekenisvol behaald resultaat voor de initiator van de ZAAK.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    # relaties
    zaak = models.ForeignKey(
        'Zaak', on_delete=models.CASCADE,
        help_text=('URL-referentie naar de ZAAK.')
    )
    statustype = models.URLField(
        _("statustype"), max_length=1000,
        help_text=_("URL-referentie naar het STATUSTYPE (in de Catalogi API).")
    )

    # extra informatie
    datum_status_gezet = models.DateTimeField(
        help_text='De datum waarop de ZAAK de status heeft verkregen.'
    )
    statustoelichting = models.TextField(
        max_length=1000, blank=True,
        help_text='Een, voor de initiator van de zaak relevante, toelichting '
                  'op de status van een zaak.'
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = 'status'
        verbose_name_plural = 'statussen'
        unique_together = ('zaak', 'datum_status_gezet')

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
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    # relaties
    zaak = models.OneToOneField(
        'Zaak', on_delete=models.CASCADE,
        help_text=('URL-referentie naar de ZAAK.')
    )
    resultaattype = models.URLField(
        _("resultaattype"), max_length=1000,
        help_text=_("URL-referentie naar het RESULTAATTYPE (in de Catalogi API).")
    )

    toelichting = models.TextField(
        max_length=1000, blank=True,
        help_text='Een toelichting op wat het resultaat van de zaak inhoudt.'
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = 'resultaat'
        verbose_name_plural = 'resultaten'

    def __str__(self):
        return "Resultaat ({})".format(self.uuid)

    def unique_representation(self):
        if not hasattr(self, '_unique_representation'):
            result_type_desc = request_object_attribute(self.resultaattype, 'omschrijving', 'resultaattype')
            self._unique_representation = f"({self.zaak.unique_representation()}) - {result_type_desc}"
        return self._unique_representation


class Rol(models.Model):
    """
    Modelleer de rol van een BETROKKENE bij een ZAAK.

    Een of meerdere BETROKKENEn hebben een of meerdere ROL(len) in een ZAAK.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey(
        'Zaak', on_delete=models.CASCADE,
        help_text=('URL-referentie naar de ZAAK.')
    )
    betrokkene = models.URLField(
        help_text="URL-referentie naar een betrokkene gerelateerd aan de ZAAK.",
        max_length=1000, blank=True
    )
    betrokkene_type = models.CharField(
        max_length=100, choices=RolTypes.choices,
        help_text='Type van de `betrokkene`.'
    )

    roltype = models.URLField(
        help_text="URL-referentie naar een roltype binnen het ZAAKTYPE van de ZAAK.",
        max_length=1000
    )
    omschrijving = models.CharField(
        _("omschrijving"), max_length=20,
        editable=False, help_text=_("Omschrijving van de aard van de ROL, afgeleid uit "
                                    "het ROLTYPE.")
    )
    omschrijving_generiek = models.CharField(
        max_length=80,
        choices=RolOmschrijving.choices,
        help_text=_("Algemeen gehanteerde benaming van de aard van de ROL, afgeleid uit het ROLTYPE."),
        editable=False
    )
    roltoelichting = models.TextField(max_length=1000)

    registratiedatum = models.DateTimeField(
        "registratiedatum", auto_now_add=True,
        help_text="De datum waarop dit object is geregistreerd."
    )
    indicatie_machtiging = models.CharField(
        max_length=40, choices=IndicatieMachtiging.choices, blank=True,
        help_text="Indicatie machtiging"
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Rollen"

    def save(self, *args, **kwargs):
        # derive text fields from RolType
        assert self.roltype, "Roltype URL must be set"

        self._derive_roltype_attributes()

        super().save(*args, **kwargs)

    def _derive_roltype_attributes(self):
        if self.omschrijving and self.omschrijving_generiek:
            return

        Client = import_string(settings.ZDS_CLIENT_CLASS)
        client = Client.from_url(self.roltype)
        client.auth = APICredential.get_auth(self.roltype)
        roltype = client.retrieve("roltype", url=self.roltype)

        self.omschrijving = roltype["omschrijving"]
        self.omschrijving_generiek = roltype["omschrijvingGeneriek"]

    def unique_representation(self):
        if self.betrokkene == '':
            return f"({self.zaak.unique_representation()}) - {self.roltoelichting}"

        betrokkene = self.betrokkene.rstrip('/') if self.betrokkene.endswith('/') else self.betrokkene
        return f"({self.zaak.unique_representation()}) - {betrokkene.rsplit('/')[-1]}"


class ZaakObject(models.Model):
    """
    Modelleer een object behorende bij een ZAAK.

    Het OBJECT in kwestie kan in verschillende andere componenten leven,
    zoals het RSGB.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey(
        'Zaak', on_delete=models.CASCADE,
        help_text=('URL-referentie naar de ZAAK.')
    )
    object = models.URLField(
        help_text='URL-referentie naar de resource die het OBJECT beschrijft.',
        max_length=1000, blank=True
    )
    relatieomschrijving = models.CharField(
        max_length=80, blank=True,
        help_text='Omschrijving van de betrekking tussen de ZAAK en het OBJECT.'
    )
    object_type = models.CharField(
        max_length=100,
        choices=ZaakobjectTypes.choices,
        help_text="Beschrijft het type OBJECT gerelateerd aan de ZAAK. Als er "
                  "geen passend type is, dan moet het type worden opgegeven "
                  "onder `objectTypeOverige`."
    )
    object_type_overige = models.CharField(
        max_length=100, blank=True, validators=[RegexValidator('[a-z\_]+')],
        help_text='Beschrijft het type OBJECT als `objectType` de waarde '
                  '"overige" heeft.'
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = 'zaakobject'
        verbose_name_plural = 'zaakobjecten'

    def _get_object(self) -> dict:
        """
        Retrieve the `Object` specified as URL in `ZaakObject.object`.

        :return: A `dict` representing the object.
        """
        if not hasattr(self, '_object'):
            object_url = self.object
            self._object = None
            if object_url:
                Client = import_string(settings.ZDS_CLIENT_CLASS)
                client = Client.from_url(object_url)
                client.auth = APICredential.get_auth(object_url)
                self._object = client.retrieve(self.object_type.lower(), url=object_url)
        return self._object

    def unique_representation(self):
        if self.object == '':
            return f"({self.zaak.unique_representation()}) - {self.relatieomschrijving}"

        object = self.object.rstrip('/') if self.object.endswith('/') else self.object
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
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey('Zaak', on_delete=models.CASCADE)
    eigenschap = models.URLField(
        help_text="URL-referentie naar de EIGENSCHAP (in de Catalogi API).",
        max_length=1000
    )
    # TODO - validatie _kan eventueel_ de configuratie van ZTC uitlezen om input
    # te valideren, en per eigenschap een specifiek datatype terug te geven.
    # In eerste instantie laten we het aan de client over om validatie en
    # type-conversie te doen.
    _naam = models.CharField(
        max_length=20,
        help_text=_("De naam van de EIGENSCHAP (overgenomen uit de Catalogi API).")
    )
    waarde = models.TextField()

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = 'zaakeigenschap'
        verbose_name_plural = 'zaakeigenschappen'

    def unique_representation(self):
        return f"({self.zaak.unique_representation()}) - {self._naam}"


class ZaakKenmerk(models.Model):
    """
    Model representatie van de Groepattribuutsoort 'Kenmerk'
    """
    zaak = models.ForeignKey('datamodel.Zaak', on_delete=models.CASCADE)
    kenmerk = models.CharField(
        max_length=40,
        help_text='Identificeert uniek de zaak in een andere administratie.')
    bron = models.CharField(
        max_length=40,
        help_text='De aanduiding van de administratie waar het kenmerk op '
                  'slaat.')

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = 'zaak kenmerk'
        verbose_name_plural = 'zaak kenmerken'


class ZaakInformatieObject(models.Model):
    """
    Modelleer INFORMATIEOBJECTen die bij een ZAAK horen.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey(
        Zaak, on_delete=models.CASCADE,
        help_text=('URL-referentie naar de ZAAK.')
    )
    informatieobject = models.URLField(
        "informatieobject",
        help_text="URL-referentie naar het INFORMATIEOBJECT (in de Documenten API), waar "
                  "ook de relatieinformatie opgevraagd kan worden.",
        max_length=1000
    )
    aard_relatie = models.CharField(
        "aard relatie", max_length=20,
        choices=RelatieAarden.choices
    )

    # relatiegegevens
    titel = models.CharField(
        "titel", max_length=200, blank=True,
        help_text="De naam waaronder het INFORMATIEOBJECT binnen het OBJECT bekend is."
    )
    beschrijving = models.TextField(
        "beschrijving", blank=True,
        help_text="Een op het object gerichte beschrijving van de inhoud van"
                  "het INFORMATIEOBJECT."
    )
    registratiedatum = models.DateTimeField(
        "registratiedatum", auto_now_add=True,
        help_text="De datum waarop de behandelende organisatie het "
                  "INFORMATIEOBJECT heeft geregistreerd bij het OBJECT. "
                  "Geldige waardes zijn datumtijden gelegen op of voor de "
                  "huidige datum en tijd."
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "zaakinformatieobject"
        verbose_name_plural = "zaakinformatieobjecten"
        unique_together = ('zaak', 'informatieobject')

    def __str__(self) -> str:
        return f"{self.zaak} - {self.informatieobject}"

    def unique_representation(self):
        if not hasattr(self, '_unique_representation'):
            io_id = request_object_attribute(self.informatieobject, 'identificatie', 'enkelvoudiginformatieobject')
            self._unique_representation = f"({self.zaak.unique_representation()}) - {io_id}"
        return self._unique_representation

    def save(self, *args, **kwargs):
        # override to set aard_relatie
        self.aard_relatie = RelatieAarden.from_object_type('zaak')
        super().save(*args, **kwargs)


class KlantContact(models.Model):
    """
    Modelleer het contact tussen een medewerker en een klant.

    Een uniek en persoonlijk contact van een burger of bedrijfsmedewerker met
    een MEDEWERKER van de zaakbehandelende organisatie over een onderhanden of
    afgesloten ZAAK.
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey(
        'Zaak', on_delete=models.CASCADE,
        help_text=_('URL-referentie naar de ZAAK.')
    )
    identificatie = models.CharField(
        max_length=14, unique=True,
        help_text='De unieke aanduiding van een KLANTCONTACT'
    )
    datumtijd = models.DateTimeField(
        help_text='De datum en het tijdstip waarop het KLANTCONTACT begint'
    )
    kanaal = models.CharField(
        blank=True, max_length=20,
        help_text='Het communicatiekanaal waarlangs het KLANTCONTACT gevoerd wordt'
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
                gen_id = self.__class__.objects.filter(identificatie=identificatie).exists()
            self.identificatie = identificatie
        super().save(*args, **kwargs)

    def unique_representation(self):
        return f'{self.identificatie}'


class ZaakBesluit(models.Model):
    """
    Model Besluit belonged to Zaak
    """
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)"
    )
    zaak = models.ForeignKey(Zaak, on_delete=models.CASCADE)
    besluit = models.URLField(
        "besluit",
        help_text="URL-referentie naar het BESLUIT (in de Besluiten API), waar "
                  "ook de relatieinformatie opgevraagd kan worden.",
        max_length=1000
    )

    objects = ZaakRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = "zaakbesluit"
        verbose_name_plural = "zaakbesluiten"
        unique_together = ('zaak', 'besluit')

    def __str__(self) -> str:
        return f"{self.zaak} - {self.besluit}"

    def unique_representation(self):
        return f"{self.zaak} - {self.besluit}"
