# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from vng_api_common.caching import ETagMixin
from vng_api_common.fields import RSINField

from openzaak.utils.mixins import APIMixin

from .validators import validate_uppercase


class CatalogusManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)


class Catalogus(ETagMixin, APIMixin, models.Model):
    """
    De verzameling van ZAAKTYPEn - incl. daarvoor relevante objecttypen - voor
    een Domein die als één geheel beheerd wordt.

    **Toelichting objecttype**

    Voor de inzet van de CATALOGUS in één uitvoerende organisatie (bijv. een gemeente) gaat KING ervan uit dat binnen
    de organisatie één CATALOGUS wordt gebruikt met alle ZAAKTYPEn van de organisatie. De unieke identificatie in dit
    voorbeeld wordt dan de combinatie van het Domein 'Gemeente', gevolgd door het RSIN van de betreffende gemeente.
    Standaardiserende organisaties zullen mogelijk meerdere catalogi willen publiceren en beheren. Denk aan een
    ministerie dat voor meerdere sectoren een CATALOGUS aanlegt. Via het Domein-attribuut krijgt zo elke CATALOGUS
    toch een unieke identificatie.

    KING bepaalt niet op voorhand welke waarden 'Domein' kan aannemen, maar registreert wel alle gebruikte waarden.
    """

    naam = models.CharField(
        _("naam"),
        blank=True,
        max_length=200,
        help_text=_("De benaming die is gegeven aan de zaaktypecatalogus."),
    )

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    # TODO [KING]: "Voor de waardenverzameling wordt door KING een waardenlijst beheerd waarin wordt
    # bijgehouden welke afkorting welk domein betreft." ZTC 2.1, blz 42 - Waar dan?
    domein = models.CharField(  # waardenverzameling hoofdletters
        _("domein"),
        max_length=5,
        validators=[validate_uppercase],
        help_text=_(
            "Een afkorting waarmee wordt aangegeven voor welk domein "
            "in een CATALOGUS ZAAKTYPEn zijn uitgewerkt."
        ),
    )
    rsin = RSINField(
        _("rsin"),
        help_text=_(
            "Het door een kamer toegekend uniek nummer voor de INGESCHREVEN "
            "NIET-NATUURLIJK PERSOON die de eigenaar is van een CATALOGUS."
        ),
        db_index=True,
    )
    contactpersoon_beheer_naam = models.CharField(
        _("naam"),
        max_length=40,
        help_text=_(
            "De naam van de contactpersoon die verantwoordelijk is voor het beheer van de CATALOGUS."
        ),
    )
    contactpersoon_beheer_telefoonnummer = models.CharField(
        _("telefoonnummer"),
        max_length=20,
        blank=True,
        help_text=_(
            "Het telefoonnummer van de contactpersoon die verantwoordelijk "
            "is voor het beheer van de CATALOGUS."
        ),
    )
    # specificatie waardenverzameling conform RFC 5321 en RFC 5322
    contactpersoon_beheer_emailadres = models.EmailField(
        _("emailadres"),
        max_length=254,
        blank=True,
        help_text=_(
            "Het emailadres van de contactpersoon die verantwoordelijk is voor het beheer van de CATALOGUS."
        ),
    )

    versie = models.CharField(
        _("versie"),
        blank=True,
        max_length=20,
        help_text=_(
            "Versie-aanduiding van de van toepassing zijnde zaaktypecatalogus."
        ),
    )

    begindatum_versie = models.DateField(
        _("begindatum versie"),
        blank=True,
        null=True,
        help_text=_(
            "Datum waarop de versie van de zaaktypecatalogus van toepassing is geworden."
        ),
    )

    objects = CatalogusManager()

    class Meta:
        unique_together = ("domein", "rsin")
        verbose_name = _("catalogus")
        verbose_name_plural = _("catalogi")

    def natural_key(self):
        return (str(self.uuid),)

    def __str__(self):
        return self.naam
