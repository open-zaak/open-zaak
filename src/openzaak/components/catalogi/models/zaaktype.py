# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _

from django_better_admin_arrayfield.models.fields import ArrayField
from vng_api_common.descriptors import GegevensGroepType
from vng_api_common.fields import VertrouwelijkheidsAanduidingField
from vng_api_common.models import APIMixin
from vng_api_common.utils import generate_unique_identification
from vng_api_common.validators import alphanumeric_excluding_diacritic

from openzaak.components.autorisaties.models import AutorisatieSpec
from openzaak.utils.fields import DurationField

from ..constants import InternExtern
from ..managers import SyncAutorisatieManager
from .mixins import ConceptMixin, GeldigheidMixin


class ZaakType(APIMixin, ConceptMixin, GeldigheidMixin, models.Model):
    """
    Het geheel van karakteristieke eigenschappen van zaken van eenzelfde soort

    Toelichting objecttype
    Het betreft de indeling of groepering van zaken naar hun aard, zoals “Behandelen aanvraag
    bouwvergunning” en “Behandelen aanvraag ontheffing parkeren”. Wat in een individueel geval
    een zaak is, waar die begint en waar die eindigt, wordt bekeken vanuit het perspectief van de
    initiator van de zaak (burger, bedrijf, medewerker, etc.). Het traject van (aan)vraag cq.
    aanleiding voor de zaak tot en met de levering van de producten/of diensten die een passend
    antwoord vormen op die aanleiding, bepaalt de omvang en afbakening van de zaak en
    daarmee van het zaaktype. Hiermee komt de afbakening van een zaaktype overeen met een
    bedrijfsproces: ‘van klant tot klant’. Dit betekent ondermeer dat onderdelen van
    bedrijfsprocessen geen zelfstandige zaken vormen. Het betekent ook dat een aanleiding die
    niet leidt tot de start van de uitvoering van een bedrijfsproces, niet leidt tot een zaak (deze
    wordt behandeld in het kader van een reeds lopende zaak).
    Zie ook de toelichtingen bij de relatiesoorten ‘ZAAKTYPE is deelzaaktype van ZAAKTYPE’ en
    ‘ZAAKTYPE heeft gerelateerd ZAAKTYPE’ voor wat betreft zaaktypen van deelzaken
    respectievelijk gerelateerde zaken.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    identificatie = models.CharField(
        _("identificatie"),
        max_length=50,
        blank=True,
        help_text=_(
            "Unieke identificatie van het ZAAKTYPE binnen de CATALOGUS waarin het ZAAKTYPE voorkomt."
        ),
        validators=[alphanumeric_excluding_diacritic],
        db_index=True,
    )
    zaaktype_omschrijving = models.CharField(
        _("omschrijving"),
        max_length=80,
        help_text=_("Omschrijving van de aard van ZAAKen van het ZAAKTYPE."),
    )
    # TODO [KING]: waardenverzameling zoals vastgelegt in CATALOGUS, wat is deze waardeverzameling dan?
    zaaktype_omschrijving_generiek = models.CharField(
        _("omschrijving generiek"),
        max_length=80,
        blank=True,
        help_text=_(
            "Algemeen gehanteerde omschrijving van de aard van ZAAKen van het ZAAKTYPE"
        ),
    )
    vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduidingField(
        _("vertrouwelijkheidaanduiding"),
        help_text=_(
            "Aanduiding van de mate waarin zaakdossiers van ZAAKen van "
            "dit ZAAKTYPE voor de openbaarheid bestemd zijn. Indien de zaak bij het "
            "aanmaken geen vertrouwelijkheidaanduiding krijgt, dan wordt deze waarde gezet."
        ),
    )
    doel = models.TextField(
        _("doel"),
        help_text=_(
            "Een omschrijving van hetgeen beoogd is te bereiken met een zaak van dit zaaktype."
        ),
    )
    aanleiding = models.TextField(
        _("aanleiding"),
        help_text=_(
            "Een omschrijving van de gebeurtenis die leidt tot het "
            "starten van een ZAAK van dit ZAAKTYPE."
        ),
    )
    toelichting = models.TextField(
        _("toelichting"),
        blank=True,
        help_text=_(
            "Een eventuele toelichting op dit zaaktype, zoals een beschrijving "
            "van het procesverloop op de hoofdlijnen."
        ),
    )
    indicatie_intern_of_extern = models.CharField(
        _("indicatie intern of extern"),
        max_length=6,
        choices=InternExtern.choices,
        help_text=_(
            "Een aanduiding waarmee onderscheid wordt gemaakt tussen "
            "ZAAKTYPEn die Intern respectievelijk Extern geïnitieerd worden. "
            "Indien van beide sprake kan zijn, dan prevaleert de externe initiatie."
        ),
    )
    handeling_initiator = models.CharField(
        _("handeling initiator"),
        max_length=20,
        help_text=_(
            "Werkwoord dat hoort bij de handeling die de initiator verricht bij dit zaaktype. "
            "Meestal 'aanvragen', 'indienen' of 'melden'. Zie ook het IOB model op "
            "https://www.gemmaonline.nl/index.php/Imztc_2.1/doc/attribuutsoort/zaaktype.handeling_initiator"
        ),
    )
    onderwerp = models.CharField(
        _("onderwerp"),
        max_length=80,
        help_text=_(
            "Het onderwerp van ZAAKen van dit ZAAKTYPE. In veel gevallen nauw gerelateerd aan de product- of "
            "dienstnaam uit de Producten- en Dienstencatalogus (PDC). Bijvoorbeeld: 'Evenementenvergunning', "
            "'Geboorte', 'Klacht'. Zie ook het IOB model op "
            "https://www.gemmaonline.nl/index.php/Imztc_2.1/doc/attribuutsoort/zaaktype.onderwerp"
        ),
    )
    handeling_behandelaar = models.CharField(
        _("handeling behandelaar"),
        max_length=20,
        help_text=_(
            "Werkwoord dat hoort bij de handeling die de behandelaar verricht bij het afdoen van ZAAKen van "
            "dit ZAAKTYPE. Meestal 'behandelen', 'uitvoeren', 'vaststellen' of 'onderhouden'. "
            "Zie ook het IOB model op "
            "https://www.gemmaonline.nl/index.php/Imztc_2.1/doc/attribuutsoort/zaaktype.handeling_behandelaar"
        ),
    )
    doorlooptijd_behandeling = DurationField(
        _("doorlooptijd behandeling"),
        help_text=_(
            "De periode waarbinnen volgens wet- en regelgeving een ZAAK van het ZAAKTYPE "
            "afgerond dient te zijn, in kalenderdagen."
        ),
    )
    servicenorm_behandeling = DurationField(
        _("servicenorm behandeling"),
        blank=True,
        null=True,
        help_text=_(
            "De periode waarbinnen verwacht wordt dat een ZAAK van het ZAAKTYPE afgerond wordt conform "
            "de geldende servicenormen van de zaakbehandelende organisatie(s)."
        ),
    )
    opschorting_en_aanhouding_mogelijk = models.BooleanField(
        _("opschorting/aanhouding mogelijk"),
        help_text=_(
            "Aanduiding die aangeeft of ZAAKen van dit mogelijk ZAAKTYPE "
            "kunnen worden opgeschort en/of aangehouden."
        ),
    )
    verlenging_mogelijk = models.BooleanField(
        _("verlenging mogelijk"),
        help_text=_(
            "Aanduiding die aangeeft of de Doorlooptijd behandeling van "
            "ZAAKen van dit ZAAKTYPE kan worden verlengd."
        ),
    )
    verlengingstermijn = DurationField(
        _("verlengingstermijn"),
        blank=True,
        null=True,
        help_text=_(
            "De termijn (typisch een aantal dagen) waarmee de Doorlooptijd "
            "behandeling van ZAAKen van dit ZAAKTYPE kan worden verlengd. Mag "
            "alleen een waarde bevatten als verlenging mogelijk is."
        ),
    )

    trefwoorden = ArrayField(
        models.CharField(_("trefwoord"), max_length=30),
        blank=True,
        default=list,
        help_text=_(
            "Een trefwoord waarmee ZAAKen van het ZAAKTYPE kunnen worden gekarakteriseerd."
        ),
        db_index=True,
    )
    publicatie_indicatie = models.BooleanField(
        _("publicatie indicatie"),
        help_text=_(
            "Aanduiding of (het starten van) een ZAAK dit ZAAKTYPE gepubliceerd moet worden."
        ),
    )
    publicatietekst = models.TextField(
        _("publicatietekst"),
        blank=True,
        help_text=_(
            "De generieke tekst van de publicatie van ZAAKen van dit ZAAKTYPE."
        ),
    )
    verantwoordingsrelatie = ArrayField(
        models.CharField(_("verantwoordingsrelatie"), max_length=40),
        blank=True,
        default=list,
        help_text=_(
            "De relatie tussen ZAAKen van dit ZAAKTYPE en de beleidsmatige en/of financiële verantwoording."
        ),
    )
    versiedatum = models.DateField(
        _("versiedatum"),
        help_text=_(
            "De datum waarop de (gewijzigde) kenmerken van het ZAAKTYPE geldig zijn geworden"
        ),
    )

    #
    # groepsattribuutsoorten
    #
    # TODO: should have shape validator, because the API resources need to conform
    producten_of_diensten = ArrayField(
        models.URLField(_("URL naar product/dienst"), max_length=1000),
        help_text=_(
            "Het product of de dienst die door ZAAKen van dit ZAAKTYPE wordt voortgebracht."
        ),
    )

    # TODO: validate shape & populate?
    selectielijst_procestype = models.URLField(
        _("selectielijst procestype"),
        blank=True,
        help_text=_(
            "URL-referentie naar een vanuit archiveringsoptiek onderkende groep processen met dezelfde "
            "kenmerken (PROCESTYPE in de Selectielijst API)."
        ),
    )
    selectielijst_procestype_jaar = models.PositiveIntegerField(
        help_text=_("Het jaartal waartoe het procestype behoort."),
        blank=True,
        null=True,
    )
    referentieproces_naam = models.CharField(
        _("referentieprocesnaam"),
        max_length=80,
        help_text=_("De naam van het Referentieproces."),
    )
    referentieproces_link = models.URLField(
        _("referentieproceslink"),
        blank=True,
        help_text=_("De URL naar de beschrijving van het Referentieproces"),
    )
    referentieproces = GegevensGroepType(
        {"naam": referentieproces_naam, "link": referentieproces_link},
        optional=("link",),
    )

    #
    # relaties
    #
    deelzaaktypen = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="hoofdzaaktypen",
        help_text=_(
            "De ZAAKTYPE(n) waaronder ZAAKen als deelzaak kunnen voorkomen bij "
            "ZAAKen van dit ZAAKTYPE."
        ),
    )
    catalogus = models.ForeignKey(
        "catalogi.Catalogus",
        # verbose_name=_("maakt deel uit van"),
        on_delete=models.CASCADE,
        help_text=_("URL-referentie naar de CATALOGUS waartoe dit ZAAKTYPE behoort."),
    )

    objects = SyncAutorisatieManager()

    IDENTIFICATIE_PREFIX = "ZAAKTYPE"

    class Meta:
        verbose_name = _("Zaaktype")
        verbose_name_plural = _("Zaaktypen")

    def __str__(self):
        return "{} ({})".format(
            self.zaaktype_omschrijving, "CONCEPT" if self.concept else self.versiedatum
        )

    @transaction.atomic
    def save(self, *args, **kwargs):
        # sync after creating new objects
        if not self.pk:
            transaction.on_commit(AutorisatieSpec.sync)

        if not self.identificatie:
            self.identificatie = generate_unique_identification(self, "versiedatum")

        if not self.verlenging_mogelijk:
            self.verlengingstermijn = None
        elif not self.verlengingstermijn:
            raise ValueError(
                "'verlengingstermijn' must be set if 'verlenging_mogelijk' is set."
            )

        super().save(*args, **kwargs)

    def clean(self):
        from ..utils import compare_relativedeltas, get_overlapping_zaaktypes

        super().clean()

        if self.verlenging_mogelijk and not self.verlengingstermijn:
            raise ValidationError(
                "'verlengingstermijn' moet ingevuld zijn als 'verlenging_mogelijk' gezet is."
            )

        # self.doorlooptijd_behandeling is empty if there are validation errors,
        # which would trigger a TypeError on the comparison
        if (
            self.doorlooptijd_behandeling
            and self.servicenorm_behandeling  # noqa
            and compare_relativedeltas(
                self.servicenorm_behandeling, self.doorlooptijd_behandeling
            )
        ):  # noqa
            raise ValidationError(
                "'Servicenorm behandeling' periode mag niet langer zijn dan "
                "de periode van 'Doorlooptijd behandeling'."
            )

        if self.catalogus_id and self.datum_begin_geldigheid:
            query = get_overlapping_zaaktypes(
                self.catalogus,
                self.zaaktype_omschrijving,
                self.datum_begin_geldigheid,
                self.datum_einde_geldigheid,
                self,
            )

            # regel voor zaaktype omschrijving
            if query.exists():
                raise ValidationError(
                    "Zaaktype versies (dezelfde omschrijving) mogen geen "
                    "overlappende geldigheid hebben."
                )

    def get_absolute_api_url(self, request=None, **kwargs) -> str:
        kwargs["version"] = "1"
        return super().get_absolute_api_url(request=request, **kwargs)
