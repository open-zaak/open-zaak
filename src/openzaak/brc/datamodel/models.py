import logging
import uuid as _uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from vng_api_common.fields import RSINField
from vng_api_common.models import APIMixin
from vng_api_common.utils import (
    generate_unique_identification, request_object_attribute
)
from vng_api_common.validators import (
    UntilTodayValidator, alphanumeric_excluding_diacritic
)

from .constants import RelatieAarden, VervalRedenen
from .query import BesluitQuerySet, BesluitRelatedQuerySet

logger = logging.getLogger(__name__)


class Besluit(APIMixin, models.Model):
    uuid = models.UUIDField(default=_uuid.uuid4)

    identificatie = models.CharField(
        'identificatie', max_length=50, blank=True,
        validators=[alphanumeric_excluding_diacritic],
        help_text="Identificatie van het besluit binnen de organisatie die "
                  "het besluit heeft vastgesteld. Indien deze niet opgegeven is, "
                  "dan wordt die gegenereerd."
    )
    verantwoordelijke_organisatie = RSINField(
        'verantwoordelijke organisatie',
        help_text="Het RSIN van de niet-natuurlijk persoon zijnde de "
                  "organisatie die het besluit heeft vastgesteld."
    )

    besluittype = models.URLField(
        'besluittype',
        help_text="URL-referentie naar het BESLUITTYPE (in de Catalogi API)."
    )
    zaak = models.URLField(
        'zaak', blank=True,  # een besluit kan niet bij een zaak horen (zoals raadsbesluit)
        help_text="URL-referentie naar de ZAAK (in de Zaken API) waarvan dit besluit uitkomst is."
    )

    datum = models.DateField(
        'datum', validators=[UntilTodayValidator()],
        help_text="De beslisdatum (AWB) van het besluit."
    )
    toelichting = models.TextField(
        'toelichting', blank=True,
        help_text="Toelichting bij het besluit."
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
        'bestuursorgaan', max_length=50, blank=True,
        help_text="Een orgaan van een rechtspersoon krachtens publiekrecht "
                  "ingesteld of een persoon of college, met enig openbaar gezag "
                  "bekleed onder wiens verantwoordelijkheid het besluit "
                  "vastgesteld is."
    )

    ingangsdatum = models.DateField(
        'ingangsdatum',
        help_text="Ingangsdatum van de werkingsperiode van het besluit."
    )
    vervaldatum = models.DateField(
        'vervaldatum', null=True, blank=True,
        help_text="Datum waarop de werkingsperiode van het besluit eindigt."
    )
    vervalreden = models.CharField(
        'vervalreden', max_length=30, blank=True,
        choices=VervalRedenen.choices,
        help_text=_("De omschrijving die aangeeft op grond waarvan het besluit is of komt te vervallen.")
    )
    publicatiedatum = models.DateField(
        'publicatiedatum', null=True, blank=True,
        help_text="Datum waarop het besluit gepubliceerd wordt."
    )
    verzenddatum = models.DateField(
        'verzenddatum', null=True, blank=True,
        help_text="Datum waarop het besluit verzonden is."
    )
    # TODO: validator
    # Afleidbaar gegeven (uit BESLUITTYPE.Reactietermijn en
    # BESLUIT.Besluitdatum)
    # .. note: (rekening houdend met weekend- en feestdagen
    uiterlijke_reactiedatum = models.DateField(
        'uiterlijke reactiedatum', null=True, blank=True,
        help_text="De datum tot wanneer verweer tegen het besluit mogelijk is."
    )
    _zaakbesluit = models.URLField(
        'zaakbesluit', blank=True,
        help_text="Link to the related object in the ZRC API"
    )

    objects = BesluitQuerySet.as_manager()

    class Meta:
        verbose_name = 'besluit'
        verbose_name_plural = 'besluiten'
        unique_together = (
            ('identificatie', 'verantwoordelijke_organisatie'),
        )

    def __str__(self):
        return f"{self.verantwoordelijke_organisatie} - {self.identificatie}"

    def save(self, *args, **kwargs):
        if not self.identificatie:
            self.identificatie = generate_unique_identification(self, "datum")
        super().save(*args, **kwargs)

    def unique_representation(self):
        return f"{self.identificatie}"


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
        unique=True,
        default=_uuid.uuid4,
        help_text="Unieke resource identifier (UUID4)")

    besluit = models.ForeignKey(
        'besluit', on_delete=models.CASCADE,
        help_text="URL-referentie naar het BESLUIT."
    )
    informatieobject = models.URLField(
        'informatieobject',
        help_text="URL-referentie naar het INFORMATIEOBJECT (in de Documenten "
                  "API) waarin (een deel van) het besluit beschreven is.",
        max_length=1000
    )
    aard_relatie = models.CharField(
        "aard relatie", max_length=20,
        choices=RelatieAarden.choices
    )

    objects = BesluitRelatedQuerySet.as_manager()

    class Meta:
        verbose_name = 'besluitinformatieobject'
        verbose_name_plural = 'besluitinformatieobjecten'
        unique_together = (
            ('besluit', 'informatieobject'),
        )

    def __str__(self):
        return str(self.uuid)

    def save(self, *args, **kwargs):
        # override to set aard_relatie
        self.aard_relatie = RelatieAarden.from_object_type('besluit')
        super().save(*args, **kwargs)

    def unique_representation(self):
        if not hasattr(self, '_unique_representation'):
            io_id = request_object_attribute(self.informatieobject, 'identificatie', 'enkelvoudiginformatieobject')
            self._unique_representation = f"({self.besluit.unique_representation()}) - {io_id}"
        return self._unique_representation
