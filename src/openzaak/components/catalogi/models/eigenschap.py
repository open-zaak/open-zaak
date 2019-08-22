import uuid
from decimal import Decimal, InvalidOperation

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .choices import FormaatChoices
from .validators import (
    validate_kardinaliteit,
    validate_letters_numbers_underscores,
    validate_letters_numbers_underscores_spaces,
)


class EigenschapSpecificatie(models.Model):
    """
    Met de ‘subattributen’ (van deze groepattribuutsoort) Groep, Formaat, Lengte, Kardinaliteit en Waardenverzameling
    wordt een eigenschap gedetailleerd gespecificeerd. Dit vindt alleen plaats als de eigenschap niet gespecificeerd is
    door middel van het groepattribuutsoort ‘Referentie naar eigenschap’.
    """

    groep = models.CharField(  # waardenverzameling Letters, cijfers en liggende streepjes
        _("groep"),
        max_length=32,
        blank=True,
        validators=[validate_letters_numbers_underscores],
        help_text=_(
            "Benaming van het object of groepattribuut waarvan de EIGENSCHAP een "
            "inhoudelijk gegeven specificeert."
        ),
    )
    # waardenverzameling gedefinieerd als tekst, getal, datum (jjjjmmdd), datum/tijd (jjjjmmdduummss), met AN20
    formaat = models.CharField(
        _("formaat"),
        max_length=20,
        choices=FormaatChoices.choices,
        help_text=_(
            "Het soort tekens waarmee waarden van de EIGENSCHAP kunnen worden vastgelegd."
        ),
    )
    lengte = models.CharField(
        _("lengte"),
        max_length=14,
        help_text=_(
            "Het aantal karakters (lengte) waarmee waarden van de EIGENSCHAP worden vastgelegd."
        ),
    )
    kardinaliteit = models.CharField(
        _("kardinaliteit"),
        max_length=3,
        validators=[validate_kardinaliteit],
        help_text=_(
            "Het aantal mogelijke voorkomens van waarden van deze EIGENSCHAP bij een zaak van het ZAAKTYPE."
        ),
    )

    waardenverzameling = ArrayField(
        models.CharField(_("waardenverzameling"), max_length=100),
        blank=True,
        help_text=_("Waarden die deze EIGENSCHAP kan hebben."),
    )

    class Meta:
        verbose_name = _("Eigenschap specificatie")
        verbose_name_plural = _("Eigenschap specificaties")

    def clean(self):
        """
        waardenverzameling voor veld lengte hangt af van formaat

        Als Formaat = tekst: 0-255
        Als Formaat = getal: n,m (n: aantal cijfers geheel getal, m:
        aantal decimalen)
        Als Formaat = datum: 8
        Als Formaat = datum/tijd: 14
        """
        if self.formaat == FormaatChoices.tekst:
            try:
                error = not (0 <= int(self.lengte) <= 255)
            except Exception:  # (ValueError, TypeError) ?
                error = True
            if error:
                raise ValidationError(
                    _(
                        "Als formaat tekst is, moet de lengte een getal tussen de 0 en 255 zijn."
                    )
                )

        elif self.formaat == FormaatChoices.getal:
            try:  # specificatie spreekt over kommagescheiden decimaal, wij nemen echter aan dat het punt gescheiden is
                Decimal(self.lengte)
            except (InvalidOperation, TypeError):
                raise ValidationError(
                    _(
                        "Als formaat getal is, moet de lengte een (kommagescheiden) getal zijn."
                    )
                )

        elif self.formaat == FormaatChoices.datum:
            if self.lengte != 8:
                raise ValidationError(_("Als formaat datum is, moet de lengte 8 zijn."))

        elif self.formaat == FormaatChoices.datum_tijd:
            if self.lengte != 14:
                raise ValidationError(
                    _("Als formaat datum/tijd is, moet de lengte 14 zijn.")
                )


class EigenschapReferentie(models.Model):
    """
    Met de ‘subattributen’ (van deze groepattribuutsoort) Objecttype, Informatiemodel, Namespace, Schemalocatie, X-path
    element en Entiteittype wordt een eigenschap gespecificeerd door te refereren naar een berichtenmodel cq. namespace
    en, bij voorkeur ook, een informatiemodel. Dit vindt alleen plaats als de eigenschap niet gespecificeerd is door
    middel van het groepattribuutsoort ‘Specificatie van eigenschap’. Met de naam van de eigenschap zijn de metagegevens
    van de eigenschap (herkomst, formaat, waardenverzameling e.d.) te ontlenen aan het desbetreffende informatiemodel.
    De specificatie dwingt niet af dat er persé sprake moet zijn van een informatiemodel. Wel is een consequentie dat er
    een XML-schema is waarin de, bij een zaaktype te specificeren, eigenschap is opgenomen. Verwijzen naar zowel een
    informatie- als een berichtenmodel is evenwel een waarborg voor een robuuste gegevensuitwisseling.
    """

    objecttype = models.CharField(  # letters, cijfers, spaties, liggend streepje
        _("objecttype"),
        max_length=40,
        blank=True,
        null=True,
        validators=[validate_letters_numbers_underscores_spaces],
        help_text=_(
            "De naam van het objecttype waarbij de eigenschap is gemodelleerd in het informatiemodel "
            "waarvan het objecttype deel uit maakt."
        ),
    )
    informatiemodel = models.CharField(  # letters, cijfers, liggend streepje
        _("informatiemodel"),
        max_length=80,
        blank=True,
        null=True,
        validators=[validate_letters_numbers_underscores],
        help_text=_(
            "De naam en de versie van het informatiemodel waarin de eigenschap is gemodelleerd."
        ),
    )
    namespace = models.CharField(
        _("namespace"),
        max_length=200,
        help_text=_("De naam van het schema waarin de eigenschap is opgenomen."),
    )
    schemalocatie = models.CharField(
        _("schemalocatie"),
        max_length=200,
        help_text=_("De locatie van het XML-schema behorend bij de Namespace"),
    )
    x_path_element = models.CharField(
        _("x path element"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_(
            "De naam van de eigenschap en het pad daarnaar toe in het XML-schema behorend bij de namespace."
        ),
    )
    entiteittype = models.CharField(
        _("entiteittype"),
        max_length=80,
        help_text=_(
            "De naam van de XML-constructie in het XML-schema behorend bij de namespace die afgeleid is van de naam "
            "van het objecttype en waarin de eigenschap is opgenomen."
        ),
    )

    class Meta:
        verbose_name = _("Eigenschap referentie")
        verbose_name_plural = _("Eigenschap referenties")

    def clean(self):
        """
        In de specificatie hebben de volgende velden een waardenververzameling die afhangt van het xml-schema:

        namespace:      Alle uri’s van gepubliceerde xml-schema’s
        x_path_element: Alle elementen in het xml-schema zoals aangeduid met Namespace.
        entiteittype:   Alle complex types in het xml-schema zoals aangeduid met Namespace.

        Deze validatie gaan we niet implementeren
        """
        pass


class Eigenschap(models.Model):
    """
    Een relevant inhoudelijk gegeven dat bij ZAAKen van dit ZAAKTYPE geregistreerd moet kunnen worden en geen standaard
    kenmerk is van een zaak.

    **Toelichting objecttype**
    Met standaard kenmerken van een zaak worden bedoeld de attributen die in het RGBZ gespecificeerd zijn bij ZAAK en
    bij de andere daarin opgenomen objecttypen. Deze kenmerken zijn generiek d.w.z. van toepassing op elke zaak,
    ongeacht het zaaktype. Niet voor elke zaak van elk zaaktype is dit voldoende informatie voor de behandeling van de
    zaak, de besturing daarvan en om daarover informatie uit te kunnen wisselen. Zo is voor het behandelen van een
    aanvraag voor een kapvergunning informatie nodig over de locatie, het type en de diameter van de te kappen boom. Het
    RGBZ bevat reeds de locatie-kenmerken. Boomtype en Stamdiameter zijn gegevens die specifiek zijn voor zaken van dit
    zaaktype, de zaaktypespecifieke eigenschappen. Een ander voorbeeld is de evenementdatum bij de behandeling van een
    aanvraag voor een evenementenvergunning. Met het specificeren van eigenschappen wordt ten eerste beoogd
    duidelijkheid te geven over de voor een zaaktype relevante eigenschappen en wordt ten tweede beoogd die
    eigenschappen zodanig te specificeren dat waarden van deze eigenschappen in StUF-ZKN- berichten uitgewisseld kunnen
    worden. Met de attributen van het objecttype EIGENSCHAP wordt een zaaktypespecifieke eigenschap gespecificeerd. De
    attributen Eigenschapnaam en Definitie duiden de eigenschap. De eigenschap wordt gegevenstechnisch gespecificeerd
    met één van twee groepen attributen:

    a) Groep, Formaat, Lengte, Kardinaliteit en Waardenverzameling. Het attribuut ‘Groep’ maakt het mogelijk om
    eigenschappen te groeperen naar een object of een groepattribuut en, met een StUF-ZKN-bericht, de waarden van de bij
    een groep behorende eigenschappen voor meerdere objecten uit te wisselen (bijvoorbeeld een ‘kapvergunning’ voor
    meerdere bomen die ieder apart geduid worden).

    b) Objecttype, Informatiemodel, Namespace, Schemalocatie, X-path element en Entiteittype. Deze specificeren een
    eigenschap door te refereren naar een berichtenmodel en, bij voorkeur ook, een informatiemodel. De eigenschap wordt
    aldus ontleend aan een XML-schema (als onderdeel van een berichtenmodel) dat reeds bestaat of specifiek voor het
    zaaktype (of de zaaktypecatalogus) is opgesteld. Voor een goed begrip van de eigenschap is het dringend gewenst dat
    deze semantisch gespecificeerd is in een informatiemodel met het oog op eenduidig te interpreteren uitwisseling van
    waarden van de eigenschap. Het betreft het informatiemodel dat opgesteld is voor het domein waarvoor de zaaktypen
    gespecificeerd worden en op basis waarvan het XML-schema is vervaardigd.

    De specificatie ad. a ondersteunt de mogelijkheid om waarden van deze eigenschappen, bij 14een specifieke zaak, uit
    te wisselen tussen applicaties ten behoeve van gebruik van deze gegevens door de gebruikers van deze applicaties. De
    gebruikers kunnen deze gegevens interpreteren, de uitwisselende applicaties kennen deze gegevens, zonder
    voorafgaande afspraken, niet zodanig dat zij daar betrouwbaar bewerkingen op kunnen baseren anders dan tonen en
    eventueel wijzigen en opslaan. De specificatie ad. b ondersteunt de mogelijkheid om waarden van deze eigenschappen,
    bij een specifieke zaak, uit te wisselen tussen applicaties die deze gegevens (willen) kennen teneinde daarop
    betrouwbaar bewerkingen te doen of te baseren (bijvoorbeeld uit de diameter, type en plaats van de boom afleiden of
    de vergunning verleend kan worden of niet).

    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    eigenschapnaam = models.CharField(
        _("eigenschapnaam"), max_length=20, help_text=_("De naam van de EIGENSCHAP")
    )
    definitie = models.CharField(
        _("definitie"),
        max_length=255,
        help_text=_("De beschrijving van de betekenis van deze EIGENSCHAP"),
    )
    specificatie_van_eigenschap = models.ForeignKey(
        "catalogi.EigenschapSpecificatie",
        verbose_name=_("specificatie van eigenschap"),
        blank=True,
        null=True,
        help_text=_("Attribuutkenmerken van de eigenschap"),
        on_delete=models.CASCADE,
    )
    referentie_naar_eigenschap = models.ForeignKey(
        "catalogi.EigenschapReferentie",
        verbose_name=_("referentie naar eigenschap"),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text=_(
            "Verwijzing naar de standaard waarin de eigenschap is gespecificeerd"
        ),
    )
    toelichting = models.CharField(
        _("toelichting"),
        max_length=1000,
        blank=True,
        help_text=_(
            "Een toelichting op deze EIGENSCHAP en het belang hiervan voor zaken van dit ZAAKTYPE."
        ),
    )

    # shouldn't this be a M2M?
    statustype = models.ForeignKey(
        "catalogi.StatusType",
        verbose_name=_("status type"),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="heeft_verplichte_eigenschap",
        help_text=_(
            "Status type moet (onder andere) deze EIGENSCHAP hebben, voordat een "
            "STATUS van het STATUSTYPE kan worden gezet."
        ),
    )
    zaaktype = models.ForeignKey(
        "catalogi.ZaakType",
        verbose_name=_("is van"),
        help_text=_(
            "URL-referentie naar het ZAAKTYPE van de ZAAKen waarvoor deze EIGENSCHAP van belang is."
        ),
        on_delete=models.CASCADE,
    )

    class Meta:
        mnemonic = "EIG"
        unique_together = ("zaaktype", "eigenschapnaam")
        verbose_name = _("Eigenschap")
        verbose_name_plural = _("Eigenschappen")
        ordering = unique_together

        filter_fields = ("zaaktype", "eigenschapnaam")
        ordering_fields = filter_fields
        search_fields = ("eigenschapnaam", "definitie", "toelichting")

    def clean(self):
        """
        De eigenschap wordt gegevenstechnisch gespecificeerd met één van twee groepen attributen:
        - specificatie van eigenschap, of
        - referentie naar eigenschap
        """
        super().clean()

        if not (
            bool(self.specificatie_van_eigenschap)
            ^ bool(self.referentie_naar_eigenschap)
        ):  # xor
            raise ValidationError(
                _(
                    "Één van twee groepen attributen is verplicht: specificatie "
                    "van eigenschap of referentie naar eigenschap"
                )
            )

    def __str__(self):
        return "{} - {}".format(self.zaaktype, self.eigenschapnaam)
