# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import logging
import uuid as _uuid

from django.apps import apps
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_loose_fk.fields import FkOrURLField
from vng_api_common.fields import RSINField
from vng_api_common.models import APIMixin
from vng_api_common.utils import generate_unique_identification
from vng_api_common.validators import (
    UntilTodayValidator,
    alphanumeric_excluding_diacritic,
)

from openzaak.components.documenten.loaders import EIOLoader
from openzaak.loaders import AuthorizedRequestsLoader
from openzaak.utils.mixins import AuditTrailMixin

from .constants import VervalRedenen
from .query import BesluitInformatieObjectQuerySet, BesluitQuerySet

logger = logging.getLogger(__name__)

__all__ = ["Besluit", "BesluitInformatieObject"]


class Besluit(AuditTrailMixin, APIMixin, models.Model):
    uuid = models.UUIDField(
        unique=True, default=_uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    identificatie = models.CharField(
        "identificatie",
        max_length=50,
        blank=True,
        validators=[alphanumeric_excluding_diacritic],
        help_text="Identificatie van het besluit binnen de organisatie die "
        "het besluit heeft vastgesteld. Indien deze niet opgegeven is, "
        "dan wordt die gegenereerd.",
    )
    verantwoordelijke_organisatie = RSINField(
        "verantwoordelijke organisatie",
        help_text="Het RSIN van de niet-natuurlijk persoon zijnde de "
        "organisatie die het besluit heeft vastgesteld.",
        db_index=True,
    )

    _besluittype_url = models.URLField(
        _("extern besluittype"),
        blank=True,
        max_length=1000,
        help_text=_(
            "URL-referentie naar extern BESLUITTYPE (in een andere Catalogi API)."
        ),
    )
    _besluittype = models.ForeignKey(
        "catalogi.BesluitType",
        on_delete=models.CASCADE,
        help_text="URL-referentie naar het BESLUITTYPE (in de Catalogi API).",
        null=True,
        blank=True,
    )
    besluittype = FkOrURLField(
        fk_field="_besluittype",
        url_field="_besluittype_url",
        help_text="URL-referentie naar het BESLUITTYPE (in de Catalogi API).",
    )

    _zaak_url = models.URLField(
        _("externe zaak"),
        blank=True,
        max_length=1000,
        help_text="URL-referentie naar de ZAAK (in de Zaken API) waarvan dit besluit uitkomst is.",
    )
    _zaak = models.ForeignKey(
        "zaken.Zaak",
        on_delete=models.PROTECT,
        null=True,
        blank=True,  # een besluit kan niet bij een zaak horen
        help_text="URL-referentie naar de ZAAK (in de Zaken API) waarvan dit besluit uitkomst is.",
    )
    zaak = FkOrURLField(
        fk_field="_zaak",
        url_field="_zaak_url",
        blank=True,
        null=True,
        help_text="URL-referentie naar de ZAAK (in de Zaken API) waarvan dit besluit uitkomst is.",
    )

    datum = models.DateField(
        "datum",
        validators=[UntilTodayValidator()],
        help_text="De beslisdatum (AWB) van het besluit.",
    )
    toelichting = models.TextField(
        "toelichting", blank=True, help_text="Toelichting bij het besluit."
    )

    # TODO: hoe dit valideren? Beter ook objectregistratie en URL referentie?
    # Alleen de namen van bestuursorganen mogen gebruikt
    # worden die voor de desbetrreffende (sic) organisatie van
    # toepassing zijn. Voor een gemeente zijn dit
    # 'Burgemeester', 'Gemeenteraad' en 'College van B&W'.
    # Indien het, bij mandatering, een bestuursorgaan van
    # een andere organisatie betreft dan de organisatie die
    # verantwoordelijk is voor de behandeling van de zaak,
    # dan moet tevens de naam van die andere organisatie
    # vermeld worden (bijvoorbeeld "Burgemeester gemeente
    # Lent").
    bestuursorgaan = models.CharField(
        "bestuursorgaan",
        max_length=50,
        blank=True,
        help_text="Een orgaan van een rechtspersoon krachtens publiekrecht "
        "ingesteld of een persoon of college, met enig openbaar gezag "
        "bekleed onder wiens verantwoordelijkheid het besluit "
        "vastgesteld is.",
    )

    ingangsdatum = models.DateField(
        "ingangsdatum", help_text="Ingangsdatum van de werkingsperiode van het besluit."
    )
    vervaldatum = models.DateField(
        "vervaldatum",
        null=True,
        blank=True,
        help_text="Datum waarop de werkingsperiode van het besluit eindigt.",
    )
    vervalreden = models.CharField(
        "vervalreden",
        max_length=30,
        blank=True,
        choices=VervalRedenen.choices,
        help_text=_(
            "De omschrijving die aangeeft op grond waarvan het besluit is of komt te vervallen."
        ),
    )
    publicatiedatum = models.DateField(
        "publicatiedatum",
        null=True,
        blank=True,
        help_text="Datum waarop het besluit gepubliceerd wordt.",
    )
    verzenddatum = models.DateField(
        "verzenddatum",
        null=True,
        blank=True,
        help_text="Datum waarop het besluit verzonden is.",
    )
    # TODO: validator
    # Afleidbaar gegeven (uit BESLUITTYPE.Reactietermijn en
    # BESLUIT.Besluitdatum)
    # .. note: (rekening houdend met weekend- en feestdagen
    uiterlijke_reactiedatum = models.DateField(
        "uiterlijke reactiedatum",
        null=True,
        blank=True,
        help_text="De datum tot wanneer verweer tegen het besluit mogelijk is.",
    )

    _zaakbesluit_url = models.URLField(
        blank=True,
        max_length=1000,
        help_text="URL of related ZaakBesluit object in the other API",
    )

    objects = BesluitQuerySet.as_manager()

    class Meta:
        verbose_name = "besluit"
        verbose_name_plural = "besluiten"
        unique_together = (("identificatie", "verantwoordelijke_organisatie"),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # save previous zaak for triggers
        # self._previous_zaak = self.zaak

        self._previous_zaak = self._zaak
        self._previous_zaak_url = self._zaak_url

    def __str__(self):
        return f"{self.verantwoordelijke_organisatie} - {self.identificatie}"

    def save(self, *args, **kwargs):
        if not self.identificatie:
            self.identificatie = generate_unique_identification(self, "datum")

        super().save(*args, **kwargs)

    def unique_representation(self):
        return f"{self.identificatie}"

    @property
    def previous_zaak(self):
        if self._previous_zaak:
            return self._previous_zaak

        if self._previous_zaak_url:
            remote_model = apps.get_model("zaken", "Zaak")
            return AuthorizedRequestsLoader().load(
                url=self._previous_zaak_url, model=remote_model
            )

        return None


class BesluitInformatieObject(models.Model):
    """
    Aanduiding van het (de) INFORMATIEOBJECT(en) waarin
    het BESLUIT beschreven is.

    Besluiten worden veelal schriftelijk vastgelegd maar kunnen ook mondeling
    genomen zijn. Deze relatie verwijst naar het informatieobject waarin het
    besluit is vastgelegd, indien van toepassing. Mogelijkerwijs is het besluit in
    meerdere afzonderlijke informatieobjecten vastgelegd of zijn in één
    informatieobject meerdere besluiten vastgelegd.
    """

    uuid = models.UUIDField(
        unique=True, default=_uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )

    besluit = models.ForeignKey(
        Besluit, on_delete=models.CASCADE, help_text="URL-referentie naar het BESLUIT."
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
        help_text="URL-referentie naar het INFORMATIEOBJECT (in de Documenten "
        "API) waarin (een deel van) het besluit beschreven is.",
    )
    informatieobject = FkOrURLField(
        fk_field="_informatieobject",
        url_field="_informatieobject_url",
        loader=EIOLoader(),
        help_text=_(
            "URL-referentie naar het INFORMATIEOBJECT (in de Documenten "
            "API) waarin (een deel van) het besluit beschreven is.",
        ),
    )
    _objectinformatieobject_url = models.URLField(
        blank=True,
        max_length=1000,
        help_text=_("URL of related ObjectInformatieObject object in the other API"),
    )

    objects = BesluitInformatieObjectQuerySet.as_manager()

    class Meta:
        verbose_name = "besluitinformatieobject"
        verbose_name_plural = "besluitinformatieobjecten"
        unique_together = ("besluit", "_informatieobject")
        constraints = [
            models.UniqueConstraint(
                fields=["besluit", "_informatieobject_url"],
                condition=~models.Q(_informatieobject_url=""),
                name="unique_besluit_and_external_document",
            )
        ]

    def __str__(self):
        return str(self.uuid)

    def unique_representation(self):
        besluit_repr = self.besluit.unique_representation()

        if hasattr(self.informatieobject, "identificatie"):
            doc_identificatie = self.informatieobject.identificatie
        else:
            doc_identificatie = self.informatieobject.latest_version.identificatie

        return f"({besluit_repr}) - {doc_identificatie}"
