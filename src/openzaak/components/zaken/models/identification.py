# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Open Zaak maintainers
from datetime import date

from django.db import models
from django.utils.translation import gettext_lazy as _

from vng_api_common.fields import RSINField
from vng_api_common.utils import generate_unique_identification


class ZaakIdentificatieManager(models.Manager):

    # TODO: lock entire table for duration transaction or set transaction isolation
    # level to read uncommitted - sparse identifications are okay
    def generate(self, organisation: str, date: date):
        instance = self.model()
        instance.dummy_date = date
        identification = generate_unique_identification(instance, "dummy_date")
        return self.create(identificatie=identification, organisatie=organisation)


class ZaakIdentificatie(models.Model):
    """
    Track (generated) zaak identifications in a separate table.

    This allows us to handle race conditions better.
    """

    identificatie = models.CharField(
        _("value"),
        blank=True,  # okay, since we have unique and check constraint
        max_length=40,
        help_text=_(
            "De unieke identificatie van de ZAAK binnen de organisatie "
            "die verantwoordelijk is voor de behandeling van de ZAAK."
        ),
        db_index=True,
    )
    bronorganisatie = RSINField(
        help_text=_(
            "Het RSIN van de Niet-natuurlijk persoon zijnde de "
            "organisatie die de zaak heeft gecreeerd. Dit moet een geldig "
            "RSIN zijn van 9 nummers en voldoen aan "
            "https://nl.wikipedia.org/wiki/Burgerservicenummer#11-proef"
        ),
    )

    objects = ZaakIdentificatieManager()
    IDENTIFICATIE_PREFIX = "ZAAK"

    dummy_date = None

    class Meta:
        verbose_name = _("zaak identification")
        verbose_name_plural = _("zaak identifications")
        constraints = [
            models.UniqueConstraint(
                fields=("identificatie", "bronorganisatie"),
                name="unique_bronorganisation_identification",
            ),
            models.CheckConstraint(
                check=~models.Q(identificatie=""), name="identificatie_not_empty"
            ),
        ]

    def __str__(self):
        return _("{identification} ({organisation})").format(
            identification=self.identificatie, organisation=self.bronorganisatie,
        )
