# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Open Zaak maintainers
from datetime import date

from django.db import models
from django.utils.translation import gettext_lazy as _

from vng_api_common.fields import RSINField
from vng_api_common.utils import generate_unique_identification

from openzaak.utils.db import pg_advisory_lock

LOCK_ID_IDENTIFICATION_GENERATION = "generate-zaak-identification"


class ZaakIdentificatieManager(models.Manager):
    def generate(self, organisation: str, date: date):
        """
        Generate an identification based on existing data.

        This uses a PostgreSQL-specific advisory lock, meaning that only one
        thread/process is able to generate a new identification at a time (other
        threads will simply wait until they acquire the lock after the running call
        releases it when the transaction exits).

        Note that this does NOT prevent other records from being read or even written
        to the involved table, so IntegrityError can still be raised if unique
        constraints will be violated. However, this does allow for concurrent read
        and writes with explicit identifications to different rows that don't affect
        the ID generation and should be a better option for performance than pessimistic
        locking where the entire table is locked even for reading (as otherwise the view
        of the data inside by generate_unique_identification could be stale due to new
        inserts).
        """
        with pg_advisory_lock(LOCK_ID_IDENTIFICATION_GENERATION):
            instance = self.model()
            instance.dummy_date = date
            identification = generate_unique_identification(instance, "dummy_date")
            return self.create(
                identificatie=identification, bronorganisatie=organisation
            )


class ZaakIdentificatie(models.Model):
    """
    Track (generated) zaak identifications in a separate table.

    This allows us to handle race conditions better.
    """

    identificatie = models.CharField(
        _("identification number"),
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
            identification=self.identificatie,
            organisation=self.bronorganisatie,
        )
