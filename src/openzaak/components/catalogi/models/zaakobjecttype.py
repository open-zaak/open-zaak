# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from vng_api_common.caching import ETagMixin

from .mixins import OptionalGeldigheidMixin
from .validators import validate_zaaktype_concept


class ZaakObjectType(ETagMixin, OptionalGeldigheidMixin, models.Model):
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    zaaktype = models.ForeignKey(
        "ZaakType",
        help_text=_(
            "URL-referentie naar de ZAAKTYPE waartoe dit ZAAKOBJECTTYPE behoort."
        ),
        on_delete=models.CASCADE,
    )
    ander_objecttype = models.BooleanField(
        _("Ander objecttype"),
        help_text=_(
            "Aanduiding waarmee wordt aangegeven of het ZAAKOBJECTTYPE een ander, "
            "niet in RSGB en RGBZ voorkomend, objecttype betreft."
        ),
    )
    objecttype = models.URLField(
        _("Objecttype"),
        help_text=_(
            "URL-referentie naar de OBJECTTYPE waartoe dit ZAAKOBJECTTYPE behoort."
        ),
    )
    relatie_omschrijving = models.CharField(
        _("Relatie omschrijving"),
        max_length=80,
        help_text=_(
            "Omschrijving van de betrekking van het Objecttype op zaken van het gerelateerde ZAAKTYPE."
        ),
    )
    statustype = models.ForeignKey(
        "catalogi.StatusType",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="zaakobjecttypen",
        help_text=_("URL-referentie naar het STATUSTYPE"),
    )

    class Meta:
        verbose_name = _("Zaakobjecttype")
        verbose_name_plural = _("Zaakobjecttypen")

    def clean(self):
        super().clean()

        validate_zaaktype_concept(self.zaaktype)

    def __str__(self):
        return self.relatie_omschrijving
