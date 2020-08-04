# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

import requests
from relativedeltafield import parse_relativedelta
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
    ZaakobjectTypes,
)
from vng_api_common.descriptors import GegevensGroepType

from openzaak.utils.fields import DurationField
from openzaak.utils.tests import no_fetch


class ResultaatType(models.Model):
    """
    Het betreft de indeling of groepering van resultaten van zaken van hetzelfde
    ZAAKTYPE naar hun aard, zoals 'verleend', 'geweigerd', 'verwerkt', et cetera.

    Toelichting objecttype
    Elke zaak heeft een resultaat. In een aantal gevallen valt dit resultaat samen met een besluit:
    ‘Evenementenvergunning verleend’, ‘Energiesubsidie geweigerd’, et cetera. Het komt echter
    ook voor dat zaken worden afgehandeld zonder dat er een besluit wordt genomen. Dit is
    bijvoorbeeld het geval bij aangiften (geboorte, verhuizing), meldingen (openbare ruimte), maar
    ook bij het intrekken van een aanvraag. Het resultaat van een zaak is van groot belang voor de
    archivering: het resultaattype bepaalt mede of de zaak en het bijbehorende dossier moeten
    worden vernietigd (na enige termijn) of blijvend bewaard moeten worden (en na enige termijn
    ‘overgebracht’ worden naar een archiefbewaarplaats). Met RESULTAATTYPE worden de
    mogelijke resultaten benoemd bij het desbetreffende zaaktype. Daarmee is het archiefregime
    bepaald voor het gehele zaakdossier: alle informatie over en documenten bij de zaken van het
    ZAAKTYPE.
    In uitzonderingsgevallen kan er sprake van zijn dat documenten van een bepaald
    INFORMATIEOBJECTTYPE in zaakdossiers bij zaken van het ZAAKTYPE een afwijkend
    archiefregime hebben ten opzichte van het zaakdossier. Privacy-gevoeligheid kan er reden
    voor zijn om documenten van een ZAAKTYPEINFORMATIEOBJECTTYPE eerder te vernietigen dan het
    zaakdossier als geheel. Specifieke wetgeving, zoals die voor de BAG, leidt er daarentegen toe
    dat een Omgevingsvergunning (activiteit bouwen) ten eeuwige dage bewaard moet blijven
    terwijl het zaakdossier na 20 jaar vernietigd dient te worden. De relatiesoort ‘RESULTAATTYPE
    bepaalt afwijkend archiefregime van ZAAK-INFORMATIEOBJECT-TYPE’ geeft de mogelijkheid
    deze uitzonderingsgevallen te documenteren.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    zaaktype = models.ForeignKey(
        "catalogi.ZaakType",
        # verbose_name=_("is relevant voor"),
        on_delete=models.CASCADE,
        related_name="resultaattypen",
        help_text=_(
            "URL-referentie naar het ZAAKTYPE van ZAAKen waarin resultaten van "
            "dit RESULTAATTYPE bereikt kunnen worden."
        ),
    )

    # core data - used by ZRC to calculate archival-related dates
    omschrijving = models.CharField(
        _("omschrijving"),
        max_length=20,
        help_text=_("Omschrijving van de aard van resultaten van het RESULTAATTYPE."),
    )
    resultaattypeomschrijving = models.URLField(
        _("resultaattypeomschrijving"),
        max_length=1000,
        help_text=_(
            "Algemeen gehanteerde omschrijving van de aard van resultaten van het RESULTAATTYPE. "
            "Dit moet een URL-referentie zijn naar de referenlijst van generieke "
            "resultaattypeomschrijvingen. Im ImZTC heet dit 'omschrijving generiek'"
        ),
    )
    omschrijving_generiek = models.CharField(
        _("omschrijving generiek"),
        max_length=20,
        blank=True,
        editable=False,
        help_text=_(
            "Gecachete tekstuele waarde van de generieke resultaattypeomschrijving."
        ),
    )

    # TODO: validate that this matches the Zaaktype.procestype
    selectielijstklasse = models.URLField(
        _("selectielijstklasse"),
        max_length=1000,
        help_text=_(
            "URL-referentie naar de, voor het archiefregime bij het RESULTAATTYPE relevante, "
            "categorie in de Selectielijst Archiefbescheiden (RESULTAAT in de Selectielijst API) "
            "van de voor het ZAAKTYPE verantwoordelijke overheidsorganisatie."
        ),
    )

    # derived fields from selectielijstklasse
    archiefnominatie = models.CharField(
        _("archiefnominatie"),
        default="",
        choices=Archiefnominatie.choices,
        max_length=20,
        blank=True,
        help_text=_(
            "Aanduiding die aangeeft of ZAAKen met een resultaat van "
            "dit RESULTAATTYPE blijvend moeten worden bewaard of "
            "(op termijn) moeten worden vernietigd. Indien niet expliciet "
            "opgegeven wordt dit gevuld vanuit de selectielijst."
        ),
    )

    archiefactietermijn = DurationField(
        _("archiefactietermijn"),
        null=True,
        blank=True,
        help_text=_(
            "De termijn, na het vervallen van het bedrjfsvoeringsbelang, "
            "waarna het zaakdossier (de ZAAK met alle bijbehorende "
            "INFORMATIEOBJECTen) van een ZAAK met een resultaat van dit "
            "RESULTAATTYPE vernietigd of overgebracht (naar een "
            "archiefbewaarplaats) moet worden. Voor te vernietigen "
            "dossiers betreft het de in die Selectielijst genoemde "
            "bewaartermjn. Voor blijvend te bewaren zaakdossiers "
            "betreft het de termijn vanaf afronding van de zaak tot "
            "overbrenging (de procestermijn is dan nihil)."
        ),
    )

    # TODO: validate dependencies between fields
    brondatum_archiefprocedure_afleidingswijze = models.CharField(
        _("afleidingswijze brondatum"),
        max_length=20,
        choices=Afleidingswijze.choices,
        help_text=_("Wijze van bepalen van de brondatum."),
    )
    # TODO: this could/should be validated against a remote OAS 3.0!
    brondatum_archiefprocedure_datumkenmerk = models.CharField(
        _("datumkenmerk"),
        max_length=80,
        blank=True,
        help_text=_(
            "Naam van de attribuutsoort van het procesobject dat "
            "bepalend is voor het einde van de procestermijn."
        ),
    )
    brondatum_archiefprocedure_einddatum_bekend = models.BooleanField(
        _("einddatum bekend"),
        default=False,
        help_text=_(
            "Indicatie dat de einddatum van het procesobject gedurende "
            "de uitvoering van de zaak bekend moet worden. Indien deze "
            "nog niet bekend is en deze waarde staat op `true`, dan "
            "kan de zaak (nog) niet afgesloten worden."
        ),
    )
    brondatum_archiefprocedure_objecttype = models.CharField(
        _("objecttype"),
        max_length=80,
        blank=True,
        choices=ZaakobjectTypes.choices,
        help_text=_(
            "Het soort object in de registratie dat het procesobject representeert."
        ),
    )
    # TODO: standardize content so that consumers understand this?
    brondatum_archiefprocedure_registratie = models.CharField(
        _("registratie"),
        max_length=80,
        blank=True,
        help_text=_(
            "De naam van de registratie waarvan het procesobject deel uit maakt."
        ),
    )
    brondatum_archiefprocedure_procestermijn = DurationField(
        _("procestermijn"),
        null=True,
        blank=True,
        help_text=_(
            "De periode dat het zaakdossier na afronding van de zaak "
            "actief gebruikt en/of geraadpleegd wordt ter ondersteuning "
            "van de taakuitoefening van de organisatie. Enkel relevant "
            "indien de afleidingswijze 'termijn' is."
        ),
    )

    brondatum_archiefprocedure = GegevensGroepType(
        {
            "afleidingswijze": brondatum_archiefprocedure_afleidingswijze,
            "datumkenmerk": brondatum_archiefprocedure_datumkenmerk,
            "einddatum_bekend": brondatum_archiefprocedure_einddatum_bekend,
            "objecttype": brondatum_archiefprocedure_objecttype,
            "registratie": brondatum_archiefprocedure_registratie,
            "procestermijn": brondatum_archiefprocedure_procestermijn,
        },
        optional=(
            "datumkenmerk",
            "einddatum_bekend",
            "objecttype",
            "registratie",
            "procestermijn",
        ),
        required=False,
        none_for_empty=False,
    )

    # meta-information - this is mostly informative
    toelichting = models.TextField(
        _("toelichting"),
        blank=True,
        help_text=_(
            "Een toelichting op dit RESULTAATTYPE en het belang hiervan "
            "voor ZAAKen waarin een resultaat van dit RESULTAATTYPE wordt geselecteerd."
        ),
    )

    class Meta:
        unique_together = ("zaaktype", "omschrijving")
        verbose_name = _("resultaattype")
        verbose_name_plural = _("resultaattypen")

    def save(self, *args, **kwargs):
        """
        Save some derived fields into local object as a means of caching.
        """
        if (
            self.resultaattypeomschrijving
            and self.resultaattypeomschrijving is not no_fetch
        ):
            response = requests.get(self.resultaattypeomschrijving).json()
            self.omschrijving_generiek = response["omschrijving"]

        # derive the default archiefnominatie
        if not self.archiefnominatie and self.selectielijstklasse:
            selectielijstklasse = self.get_selectielijstklasse()
            self.archiefnominatie = selectielijstklasse["waardering"]

        if not self.archiefactietermijn and self.selectielijstklasse:
            selectielijstklasse = self.get_selectielijstklasse()
            parsed_relativedelta = (
                parse_relativedelta(selectielijstklasse["bewaartermijn"])
                if selectielijstklasse["bewaartermijn"]
                else None
            )
            self.archiefactietermijn = parsed_relativedelta

        # Met de attribuutsoorten van dit groepatribuutsoort worden deze situaties
        # geparametrieerd. Dit is alleen relevant indien sprake is van de Archiefnominatie
        # "vernietigen"; voor te bewaren zaakdossiers start de Archiefactietermijn op de
        # einddatum van de zaak.
        if (
            self.archiefnominatie == Archiefnominatie.blijvend_bewaren
            and not self.brondatum_archiefprocedure_afleidingswijze
        ):
            self.brondatum_archiefprocedure_afleidingswijze = (
                Afleidingswijze.afgehandeld
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.zaaktype} - {self.omschrijving}"

    def get_selectielijstklasse(self):
        if not hasattr(self, "_selectielijstklasse"):
            # selectielijstklasse should've been validated at this point by either
            # forms or serializers
            response = requests.get(self.selectielijstklasse)
            response.raise_for_status()
            self._selectielijstklasse = response.json()
        return self._selectielijstklasse
