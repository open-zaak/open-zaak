# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_better_admin_arrayfield.models.fields import ArrayField

from ..constants import FormaatChoices
from .validators import validate_kardinaliteit, validate_letters_numbers_underscores


class EigenschapSpecificatie(models.Model):
    """
    Met de ‘subattributen’ (van deze groepattribuutsoort) Groep, Formaat, Lengte, Kardinaliteit en
    Waardenverzameling wordt een eigenschap gedetailleerd gespecificeerd. Dit vindt alleen plaats
    als de eigenschap niet gespecificeerd is door middel van het groepattribuutsoort
    ‘Referentie naar eigenschap’.
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
        default=list,
        blank=True,
        help_text=_("Waarden die deze EIGENSCHAP kan hebben."),
    )

    class Meta:
        verbose_name = _("Eigenschap specificatie")
        verbose_name_plural = _("Eigenschap specificaties")

    def __str__(self):
        return f"{self.groep} - {self.formaat} [{self.lengte}, #{self.kardinaliteit}]"

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
            try:
                Decimal(self.lengte.replace(",", "."))
            except (InvalidOperation, TypeError):
                raise ValidationError(
                    _(
                        "Als formaat getal is, moet de lengte een (kommagescheiden) getal zijn."
                    )
                )

        else:
            try:
                length = int(self.lengte)
            except ValueError:
                raise ValidationError(_("Voer een getal in als lengte"), code="invalid")

            if self.formaat == FormaatChoices.datum:
                if length != 8:
                    raise ValidationError(
                        _("Als formaat datum is, moet de lengte 8 zijn.")
                    )

            elif self.formaat == FormaatChoices.datum_tijd:
                if length != 14:
                    raise ValidationError(
                        _("Als formaat datum/tijd is, moet de lengte 14 zijn.")
                    )


class Eigenschap(models.Model):
    """
    Een relevant inhoudelijk gegeven dat bij ZAAKen van dit ZAAKTYPE geregistreerd
    moet kunnen worden en geen standaard kenmerk is van een zaak.

    **Toelichting objecttype**
    Met standaard kenmerken van een zaak worden bedoeld de attributen die in het RGBZ gespecificeerd zijn bij
    ZAAK en bij de andere daarin opgenomen objecttypen. Deze kenmerken zijn generiek d.w.z. van toepassing
    op elke zaak, ongeacht het zaaktype. Niet voor elke zaak van elk zaaktype is dit voldoende informatie
    voor de behandeling van de zaak, de besturing daarvan en om daarover informatie uit te kunnen wisselen.
    Zo is voor het behandelen van een aanvraag voor een kapvergunning informatie nodig over de locatie,
    het type en de diameter van de te kappen boom. Het RGBZ bevat reeds de locatie-kenmerken. Boomtype
    en Stamdiameter zijn gegevens die specifiek zijn voor zaken van dit zaaktype, de zaaktypespecifieke
    eigenschappen. Een ander voorbeeld is de evenementdatum bij de behandeling van een aanvraag voor
    een evenementenvergunning. Met het specificeren van eigenschappen wordt ten eerste beoogd duidelijkheid
    te geven over de voor een zaaktype relevante eigenschappen en wordt ten tweede beoogd die
    eigenschappen zodanig te specificeren dat waarden van deze eigenschappen in StUF-ZKN-
    berichten uitgewisseld kunnen worden. Met de attributen van het objecttype EIGENSCHAP
    wordt een zaaktypespecifieke eigenschap gespecificeerd. De attributen Eigenschapnaam
    en Definitie duiden de eigenschap. De eigenschap wordt gegevenstechnisch gespecificeerd
    met één van twee groepen attributen:

    a) Groep, Formaat, Lengte, Kardinaliteit en Waardenverzameling. Het attribuut ‘Groep’ maakt het mogelijk om
    eigenschappen te groeperen naar een object of een groepattribuut en, met een StUF-ZKN-bericht, de waarden
    van de bij een groep behorende eigenschappen voor meerdere objecten uit te wisselen (bijvoorbeeld een
    ‘kapvergunning’ voor meerdere bomen die ieder apart geduid worden).

    b) Objecttype, Informatiemodel, Namespace, Schemalocatie, X-path element en Entiteittype. Deze specificeren een
    eigenschap door te refereren naar een berichtenmodel en, bij voorkeur ook, een informatiemodel. De eigenschap wordt
    aldus ontleend aan een XML-schema (als onderdeel van een berichtenmodel) dat reeds bestaat of specifiek voor het
    zaaktype (of de zaaktypecatalogus) is opgesteld. Voor een goed begrip van de eigenschap is het dringend gewenst dat
    deze semantisch gespecificeerd is in een informatiemodel met het oog op eenduidig te interpreteren uitwisseling van
    waarden van de eigenschap. Het betreft het informatiemodel dat opgesteld is voor het domein waarvoor de zaaktypen
    gespecificeerd worden en op basis waarvan het XML-schema is vervaardigd.

    De specificatie ad. a ondersteunt de mogelijkheid om waarden van deze eigenschappen, bij 14een specifieke zaak, uit
    te wisselen tussen applicaties ten behoeve van gebruik van deze gegevens door de gebruikers van deze applicaties.
    De gebruikers kunnen deze gegevens interpreteren, de uitwisselende applicaties kennen deze gegevens, zonder
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
        blank=False,
        null=True,
        help_text=_("Attribuutkenmerken van de eigenschap"),
        on_delete=models.CASCADE,
    )
    toelichting = models.CharField(
        _("toelichting"),
        max_length=1000,
        blank=True,
        help_text=_(
            "Een toelichting op deze EIGENSCHAP en het belang hiervan voor zaken van dit ZAAKTYPE."
        ),
    )
    zaaktype = models.ForeignKey(
        "catalogi.ZaakType",
        # verbose_name=_("is van"),
        help_text=_(
            "URL-referentie naar het ZAAKTYPE van de ZAAKen waarvoor deze EIGENSCHAP van belang is."
        ),
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ("zaaktype", "eigenschapnaam")
        verbose_name = _("Eigenschap")
        verbose_name_plural = _("Eigenschappen")

    def __str__(self):
        return self.eigenschapnaam
