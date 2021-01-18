# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from ..constants import AardRelatieChoices, RichtingChoices


class ZaakTypeInformatieObjectType(models.Model):
    """
    ZAAK-INFORMATIEOBJECT-TYPE

    Kenmerken van de relatie ZAAKTYPE heeft relevante INFORMATIEOBJECTTYPEn.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )

    zaaktype = models.ForeignKey(
        "catalogi.Zaaktype",
        verbose_name=_("zaaktype"),
        on_delete=models.CASCADE,
        help_text=_("URL-referentie naar het ZAAKTYPE."),
    )
    informatieobjecttype = models.ForeignKey(
        "catalogi.InformatieObjectType",
        on_delete=models.CASCADE,
        verbose_name=_("informatie object type"),
        help_text=_("URL-referentie naar het INFORMATIEOBJECTTYPE."),
    )

    volgnummer = models.PositiveSmallIntegerField(
        _("volgnummer"),
        validators=[MinValueValidator(1), MaxValueValidator(999)],
        help_text=_(
            "Uniek volgnummer van het ZAAK-INFORMATIEOBJECTTYPE binnen het ZAAKTYPE."
        ),
    )
    richting = models.CharField(
        _("richting"),
        max_length=20,
        choices=RichtingChoices.choices,
        help_text=_(
            "Aanduiding van de richting van informatieobjecten van het gerelateerde INFORMATIEOBJECTTYPE "
            "bij zaken van het gerelateerde ZAAKTYPE."
        ),
        db_index=True,
    )

    # this is the relation that is described on StatusType in the specification
    # TODO: validate that statustype is in fact a status type of self.zaaktype
    statustype = models.ForeignKey(
        "catalogi.StatusType",
        verbose_name=_("status type"),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="heeft_verplichte_zit",
        help_text=_(
            "URL-referentie naar het STATUSTYPE waarbij deze INFORMATIEOBJECTTYPEn verplicht aanwezig moeten "
            "zijn."
        ),
    )

    class Meta:
        # NOTE: The uniqueness is implied in the specification.
        unique_together = ("zaaktype", "volgnummer")
        verbose_name = _("Zaak-Informatieobject-Type")
        verbose_name_plural = _("Zaak-Informatieobject-Typen")

    def __str__(self):
        return "{} - {}".format(self.zaaktype, self.volgnummer)


class ZaakTypenRelatie(models.Model):
    """
    ZAAKTYPENRELATIE

    Kenmerken van de relatie ZAAKTYPE heeft gerelateerde ZAAKTYPE.
    """

    zaaktype = models.ForeignKey(
        "catalogi.ZaakType",
        verbose_name=_("zaaktype van"),
        related_name="zaaktypenrelaties",
        on_delete=models.CASCADE,
    )

    # TODO: add (shape) validator
    gerelateerd_zaaktype = models.URLField(
        _("gerelateerd zaaktype"),
        help_text=_(
            "URL referentie naar het gerelateerde zaaktype, mogelijks in een extern ZTC."
        ),
    )
    aard_relatie = models.CharField(
        _("aard relatie"),
        max_length=15,
        choices=AardRelatieChoices.choices,
        help_text=_(
            "Omschrijving van de aard van de relatie van zaken van het "
            "ZAAKTYPE tot zaken van het andere ZAAKTYPE"
        ),
    )
    toelichting = models.CharField(
        _("toelichting"),
        max_length=255,
        blank=True,
        help_text=_(
            "Een toelichting op de aard van de relatie tussen beide ZAAKTYPEN."
        ),
    )

    class Meta:
        # NOTE: The uniqueness is not explicitly defined in specification:
        unique_together = ("zaaktype", "gerelateerd_zaaktype")
        verbose_name = _("Zaaktypenrelatie")
        verbose_name_plural = _("Zaaktypenrelaties")

    def __str__(self):
        return "{} - {}".format("zaaktype", "gerelateerd_zaaktype")
