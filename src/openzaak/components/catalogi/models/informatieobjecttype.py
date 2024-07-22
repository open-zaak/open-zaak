# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid as _uuid
from functools import partial

from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from vng_api_common.caching import ETagMixin
from vng_api_common.fields import VertrouwelijkheidsAanduidingField

from openzaak.components.autorisaties.models import CatalogusAutorisatie
from openzaak.utils.mixins import APIMixin

from ..managers import SyncAutorisatieManager
from ..query import GeldigheidQuerySet
from .mixins import ConceptMixin, GeldigheidMixin


class InformatieObjectType(
    ETagMixin, APIMixin, GeldigheidMixin, ConceptMixin, models.Model
):
    """
    Aanduiding van de aard van INFORMATIEOBJECTen zoals gehanteerd door de zaakbehandelende organisatie.

    Unieke aanduiding van CATALOGUS in combinatie met Informatieobjecttype-omschrijving.
    """

    uuid = models.UUIDField(
        unique=True, default=_uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    omschrijving = models.CharField(
        _("omschrijving"),
        max_length=80,
        help_text=_(
            "Omschrijving van de aard van informatieobjecten van dit INFORMATIEOBJECTTYPE."
        ),
    )
    informatieobjectcategorie = models.CharField(
        _("categorie"),
        max_length=80,
        help_text=_(
            "Typering van de aard van informatieobjecten van dit INFORMATIEOBJECTTYPE."
        ),
    )
    trefwoord = ArrayField(
        models.CharField(_("trefwoord"), max_length=30),
        blank=True,
        default=list,
        help_text=_(
            "Trefwoord(en) waarmee informatieobjecten van het INFORMATIEOBJECTTYPE kunnen worden "
            "gekarakteriseerd. (Gebruik een komma om waarden van elkaar te onderscheiden.)"
        ),
    )
    vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduidingField(
        _("vertrouwelijkheidaanduiding"),
        help_text=_(
            "Aanduiding van de mate waarin informatieobjecten van dit INFORMATIEOBJECTTYPE voor de "
            "openbaarheid bestemd zijn."
        ),
    )

    omschrijving_generiek_informatieobjecttype = models.CharField(
        _("informatieobjecttype omschrijving generiek"),
        max_length=80,
        blank=True,
        help_text=_("Algemeen gehanteerde omschrijving van het type informatieobject."),
    )
    omschrijving_generiek_definitie = models.CharField(
        _("definitie"),
        max_length=255,
        blank=True,
        help_text=_("Nauwkeurige beschrijving van het generieke type informatieobject"),
    )
    omschrijving_generiek_herkomst = models.CharField(
        _("herkomst"),
        max_length=12,
        blank=True,
        help_text=_(
            "De naam van de waardenverzameling, of van de beherende "
            "organisatie daarvan, waaruit de waarde is overgenomen."
        ),
    )
    omschrijving_generiek_hierarchie = models.CharField(
        _("hierarchie"),
        max_length=80,
        blank=True,
        help_text=_("De plaats in de rangorde van het informatieobjecttype."),
    )
    omschrijving_generiek_opmerking = models.CharField(
        _("opmerking"),
        max_length=255,
        blank=True,
        help_text=_("Zinvolle toelichting bij het informatieobjecttype"),
    )

    # relation fields
    catalogus = models.ForeignKey(
        "catalogi.Catalogus",
        # verbose_name=_("maakt deel uit van"),
        on_delete=models.CASCADE,
        help_text=(
            "URL-referentie naar de CATALOGUS waartoe dit INFORMATIEOBJECTTYPE behoort."
        ),
    )

    zaaktypen = models.ManyToManyField(
        "catalogi.ZaakType",
        # verbose_name=_("zaaktypen"),
        related_name="informatieobjecttypen",
        through="catalogi.ZaakTypeInformatieObjectType",
        help_text=_(
            "ZAAKTYPE met ZAAKen die relevant kunnen zijn voor dit INFORMATIEOBJECTTYPE"
        ),
    )

    objects = SyncAutorisatieManager.from_queryset(GeldigheidQuerySet)()

    class Meta:
        verbose_name = _("Informatieobjecttype")
        verbose_name_plural = _("Informatieobjecttypen")

    def __str__(self):
        representation = f"{self.omschrijving} {self.datum_begin_geldigheid}"
        if self.concept:
            representation = "{} (CONCEPT)".format(representation)
        return representation

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.pk:
            transaction.on_commit(partial(CatalogusAutorisatie.sync, [self]))
        super().save(*args, **kwargs)
