# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid as _uuid

from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _

from vng_api_common.fields import VertrouwelijkheidsAanduidingField
from vng_api_common.models import APIMixin

from openzaak.components.autorisaties.models import AutorisatieSpec

from ..managers import SyncAutorisatieManager
from .mixins import ConceptMixin, GeldigheidMixin


class InformatieObjectType(APIMixin, GeldigheidMixin, ConceptMixin, models.Model):
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
    vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduidingField(
        _("vertrouwelijkheidaanduiding"),
        help_text=_(
            "Aanduiding van de mate waarin informatieobjecten van dit INFORMATIEOBJECTTYPE voor de "
            "openbaarheid bestemd zijn."
        ),
    )
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

    objects = SyncAutorisatieManager()

    class Meta:
        unique_together = ("catalogus", "omschrijving")
        verbose_name = _("Informatieobjecttype")
        verbose_name_plural = _("Informatieobjecttypen")

    def __str__(self):
        representation = self.omschrijving
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
