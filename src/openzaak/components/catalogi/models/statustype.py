# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _


class StatusType(models.Model):
    """
    Generieke aanduiding van de aard van een STATUS

    Toelichting objecttype
    Zaken van eenzelfde zaaktype doorlopen alle dezelfde statussen, tenzij de zaak voortijdig
    beeëindigd wordt. Met STATUSTYPE worden deze statussen benoemd bij het desbetreffende
    zaaktype. De attribuutsoort ‘Doorlooptijd status’ is niet bedoeld om daarmee voor een
    individuele zaak de statussen te plannen maar om geïnteresseerden informatie te verschaffen
    over de termijn waarop normaliter een volgende status bereikt wordt.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )

    # relations
    zaaktype = models.ForeignKey(
        "ZaakType",
        # verbose_name=_("is van"),
        related_name="statustypen",
        on_delete=models.CASCADE,
        help_text=_(
            "URL-referentie naar het ZAAKTYPE van ZAAKen waarin STATUSsen van dit STATUSTYPE bereikt kunnen worden."
        ),
    )

    # attributes
    statustype_omschrijving = models.CharField(
        _("omschrijving"),
        max_length=80,
        help_text=_(
            "Een korte, voor de initiator van de zaak relevante, omschrijving van de "
            "aard van de STATUS van zaken van een ZAAKTYPE."
        ),
    )
    statustype_omschrijving_generiek = models.CharField(
        _("omschrijving generiek"),
        max_length=80,
        blank=True,
        help_text=_(
            "Algemeen gehanteerde omschrijving van de aard van STATUSsen van het STATUSTYPE"
        ),
    )
    # waardenverzameling is 0001 - 9999, omdat int('0001') == 1 als PositiveSmallIntegerField
    statustypevolgnummer = models.PositiveSmallIntegerField(
        _("statustypevolgnummer"),
        validators=[MinValueValidator(1), MaxValueValidator(9999)],
        help_text=_(
            "Een volgnummer voor statussen van het STATUSTYPE binnen een zaak."
        ),
    )
    informeren = models.BooleanField(
        _("informeren"),
        default=False,
        help_text=_(
            "Aanduiding die aangeeft of na het zetten van een STATUS van dit STATUSTYPE de Initiator moet "
            "worden geïnformeerd over de statusovergang."
        ),
    )
    statustekst = models.CharField(
        _("statustekst"),
        max_length=1000,
        blank=True,
        help_text=_(
            "De tekst die wordt gebruikt om de Initiator te informeren over het bereiken van een STATUS van "
            "dit STATUSTYPE bij het desbetreffende ZAAKTYPE."
        ),
    )
    toelichting = models.CharField(
        _("toelichting"),
        max_length=1000,
        blank=True,
        null=True,
        help_text=_("Een eventuele toelichting op dit STATUSTYPE."),
    )

    class Meta:
        unique_together = ("zaaktype", "statustypevolgnummer")
        verbose_name = _("Statustype")
        verbose_name_plural = _("Statustypen")
        ordering = ("zaaktype", "-statustypevolgnummer")

    def is_eindstatus(self):
        """
        Sorting by statustypevolgnummer desc is performed in StatusType.Meta.ordering
        """
        last_statustype = self.zaaktype.statustypen.first()
        return last_statustype == self

    def __str__(self):
        return self.statustype_omschrijving
