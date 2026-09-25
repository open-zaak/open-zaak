# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from vng_api_common.caching import ETagMixin
from zgw_consumers.models import ServiceUrlField

from openzaak.utils.fields import FkOrServiceUrlField, RelativeURLField, ServiceFkField

from ..constants import AardRelatieChoices, RichtingChoices


class ZaakTypeInformatieObjectType(ETagMixin, models.Model):
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
    _iotype_base_url = ServiceFkField(
        help_text=_("Basis deel van URL-referentie naar de externe API"),
    )
    _iotype_relative_url = RelativeURLField(
        _("informatieobjecttype relative url"),
        blank=True,
        null=True,
        help_text=_("Relatief deel van URL-referentie naar de externe API"),
    )
    _iotype_url = ServiceUrlField(
        base_field="_iotype_base_url",
        relative_field="_iotype_relative_url",
        blank=True,
        null=True,
        max_length=1000,
        help_text=_("URL to the informatieobjecttype in an external API"),
    )
    _informatieobjecttype = models.ForeignKey(
        "catalogi.InformatieObjectType",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text=_("URL-referentie naar het INFORMATIEOBJECTTYPE."),
    )
    informatieobjecttype = FkOrServiceUrlField(
        fk_field="_informatieobjecttype",
        url_field="_iotype_url",
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

    @property
    def concept(self):
        """
        Subresources of Zaaktype are implicitly concept or non-concept based on the
        value of this attribute of the Zaaktype
        """
        return self.zaaktype.concept and self.informatieobjecttype.concept

    class Meta:
        # NOTE: The uniqueness is implied in the specification.
        unique_together = ("zaaktype", "volgnummer")
        verbose_name = _("Zaak-Informatieobject-Type")
        verbose_name_plural = _("Zaak-Informatieobject-Typen")

    def __str__(self):
        return "{} - {}".format(self.zaaktype, self.volgnummer)


class BesluitTypeInformatieObjectType(models.Model):
    besluittype = models.ForeignKey(
        "catalogi.BesluitType",
        verbose_name=_("besluittype"),
        on_delete=models.CASCADE,
        help_text=_("URL-referentie naar het BESLUITTYPE."),
    )

    _iotype_base_url = ServiceFkField(
        help_text=_("Basis deel van URL-referentie naar de externe API"),
    )
    _iotype_relative_url = RelativeURLField(
        _("informatieobjecttype relative url"),
        blank=True,
        null=True,
        help_text=_("Relatief deel van URL-referentie naar de externe API"),
    )
    _iotype_url = ServiceUrlField(
        base_field="_iotype_base_url",
        relative_field="_iotype_relative_url",
        blank=True,
        null=True,
        max_length=1000,
        help_text=_("URL to the informatieobjecttype in an external API"),
    )
    _informatieobjecttype = models.ForeignKey(
        "catalogi.InformatieObjectType",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text=_("URL-referentie naar het INFORMATIEOBJECTTYPE."),
    )
    informatieobjecttype = FkOrServiceUrlField(
        fk_field="_informatieobjecttype",
        url_field="_iotype_url",
        help_text=_("URL-referentie naar het INFORMATIEOBJECTTYPE."),
    )

    class Meta:
        verbose_name = _("Besluit-Informatieobject-Type")
        verbose_name_plural = _("Besluit-Informatieobject-Typen")
        constraints = [
            models.UniqueConstraint(
                fields=["besluittype", "_informatieobjecttype"],
                name="unique_besluittype_and_local_informatieobjecttype",
            ),
            models.UniqueConstraint(
                fields=[
                    "besluittype",
                    "_iotype_base_url",
                    "_iotype_relative_url",
                ],
                condition=models.Q(_iotype_relative_url__isnull=False),
                name="unique_besluittype_and_external_informatieobjecttype",
            ),
        ]

    def __str__(self):
        return "{} - {}".format(self.besluittype, self.informatieobjecttype)


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

    @property
    def concept(self):
        """
        Subresources of Zaaktype are implicitly concept or non-concept based on the
        value of this attribute of the Zaaktype and the Informatieobjecttype
        """
        return self.zaaktype.concept

    class Meta:
        # NOTE: The uniqueness is not explicitly defined in specification:
        unique_together = ("zaaktype", "gerelateerd_zaaktype")
        verbose_name = _("Zaaktypenrelatie")
        verbose_name_plural = _("Zaaktypenrelaties")

    def __str__(self):
        return "{} - {}".format("zaaktype", "gerelateerd_zaaktype")
