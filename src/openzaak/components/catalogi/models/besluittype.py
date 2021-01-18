# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid as _uuid

from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _

from vng_api_common.models import APIMixin

from openzaak.components.autorisaties.models import AutorisatieSpec
from openzaak.utils.fields import DurationField

from ..managers import SyncAutorisatieManager
from .mixins import ConceptMixin, GeldigheidMixin


class BesluitType(APIMixin, GeldigheidMixin, ConceptMixin, models.Model):
    """
    Generieke aanduiding van de aard van een besluit.

    **Populatie**
    Alle besluittypen van de besluiten die het resultaat kunnen zijn van het
    zaakgericht werken van de behandelende organisatie(s).

    **Toelichting objecttype**
    Het betreft de indeling of groepering van besluiten naar hun aard, zoals
    bouwvergunning, ontheffing geluidhinder en monumentensubsidie.
    """

    uuid = models.UUIDField(
        unique=True, default=_uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )

    omschrijving = models.CharField(
        _("omschrijving"),
        max_length=80,
        blank=True,
        help_text=_("Omschrijving van de aard van BESLUITen van het BESLUITTYPE."),
    )

    # TODO [KING]: wat is de waardenverzameling?
    omschrijving_generiek = models.CharField(
        _("omschrijving generiek"),
        max_length=80,
        blank=True,
        help_text=_(
            "Algemeen gehanteerde omschrijving van de aard van BESLUITen van het BESLUITTYPE"
        ),
    )

    # TODO [KING]: waardenverzameling gebaseerd op de AWB, wat betekend dat?
    besluitcategorie = models.CharField(
        _("besluitcategorie"),
        max_length=40,
        blank=True,
        help_text=_("Typering van de aard van BESLUITen van het BESLUITTYPE."),
    )

    reactietermijn = DurationField(
        _("reactietermijn"),
        blank=True,
        null=True,
        help_text=_(
            "De duur (typisch een aantal dagen), gerekend vanaf de verzend- of publicatiedatum, "
            "waarbinnen verweer tegen een besluit van het besluittype mogelijk is."
        ),
    )

    publicatie_indicatie = models.BooleanField(
        _("publicatie indicatie"),
        null=False,
        help_text=_(
            "Aanduiding of BESLUITen van dit BESLUITTYPE gepubliceerd moeten worden."
        ),
    )

    publicatietekst = models.TextField(
        _("publicatietekst"),
        blank=True,
        help_text=_(
            "De generieke tekst van de publicatie van BESLUITen van dit BESLUITTYPE"
        ),
    )

    publicatietermijn = DurationField(
        _("publicatietermijn"),
        blank=True,
        null=True,
        help_text=_(
            "De duur (typisch een aantal dagen), gerekend vanaf de verzend- of publicatiedatum, "
            "dat BESLUITen van dit BESLUITTYPE gepubliceerd moeten blijven."
        ),
    )

    toelichting = models.TextField(
        _("toelichting"),
        blank=True,
        help_text=_("Een eventuele toelichting op dit BESLUITTYPE."),
    )

    catalogus = models.ForeignKey(
        "catalogi.Catalogus",
        on_delete=models.CASCADE,
        # verbose_name=_("catalogus"),
        help_text=_(
            "URL-referentie naar de CATALOGUS waartoe dit BESLUITTYPE behoort."
        ),
    )

    informatieobjecttypen = models.ManyToManyField(
        "catalogi.InformatieObjectType",
        blank=True,
        # verbose_name=_("informatieobjecttype"),
        related_name="besluittypen",
        help_text=_(
            "URL-referenties naar het INFORMATIEOBJECTTYPE van informatieobjecten waarin besluiten van dit "
            "BESLUITTYPE worden vastgelegd."
        ),
    )

    zaaktypen = models.ManyToManyField(
        "catalogi.ZaakType",
        # verbose_name=_("zaaktypen"),
        related_name="besluittypen",
        help_text=_(
            "ZAAKTYPE met ZAAKen die relevant kunnen zijn voor dit BESLUITTYPE"
        ),
    )

    objects = SyncAutorisatieManager()

    class Meta:
        verbose_name = _("besluittype")
        verbose_name_plural = _("besluittypen")
        unique_together = ("catalogus", "omschrijving")

    def __str__(self):
        representation = f"{self.catalogus} - {self.omschrijving}"
        if self.concept:
            representation = "{} (CONCEPT)".format(representation)
        return representation

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.pk:
            transaction.on_commit(AutorisatieSpec.sync)
        super().save(*args, **kwargs)

    def get_absolute_api_url(self, request=None, **kwargs) -> str:
        kwargs["version"] = "1"
        return super().get_absolute_api_url(request=request, **kwargs)
