# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.fields import VertrouwelijkheidsAanduidingField
from vng_api_common.models import APIMixin


class ApplicatieManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)


class Applicatie(APIMixin, models.Model):
    """
    Client level of authorization
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text="Unique resource identifier (UUID4)"
    )
    client_ids = ArrayField(
        models.CharField(max_length=50),
        verbose_name=_("client IDs"),
        help_text=_("Comma separated list of consumer identifiers (client_ids)"),
    )
    label = models.CharField(
        max_length=100,
        help_text=_(
            "A human readable representation of the application, for end users."
        ),
    )
    heeft_alle_autorisaties = models.BooleanField(
        _("has all authorizations"),
        default=False,
        help_text=_(
            "If all authorizations are given to this applicatie, no individual "
            "permissions have to be configured. Only enable this if you "
            "fully trust the consumer."
        ),
    )

    objects = ApplicatieManager()

    class Meta:
        ordering = ["pk"]
        verbose_name = _("applicatie")
        verbose_name_plural = _("applicaties")

    def natural_key(self):
        return (str(self.uuid),)

    def __str__(self):
        return f"Applicatie ({self.label})"


CATALOGUS_AUTORISATIE_COMPONENTS = [
    ComponentTypes.zrc,
    ComponentTypes.drc,
    ComponentTypes.brc,
]


class CatalogusAutorisatieManager(models.Manager):
    def get_by_natural_key(self, applicatie, catalogus, component):
        return self.get(applicatie=applicatie, catalogus=catalogus, component=component)


class CatalogusAutorisatie(models.Model):
    applicatie = models.ForeignKey(
        Applicatie,
        on_delete=models.CASCADE,
        help_text=_("The application to which this authorisation belongs"),
    )
    catalogus = models.ForeignKey(
        "catalogi.Catalogus",
        on_delete=models.CASCADE,
        help_text=_("The catalogi for which this authorisation gives permissions"),
    )

    component = models.CharField(
        _("component"),
        max_length=50,
        choices=[
            choice
            for choice in ComponentTypes.choices
            if choice[0] in CATALOGUS_AUTORISATIE_COMPONENTS
        ],
        help_text=_("Component waarop autorisatie van toepassing is."),
    )
    scopes = ArrayField(
        models.CharField(max_length=100),
        verbose_name=_("scopes"),
        help_text=_("Komma-gescheiden lijst van scope labels."),
    )
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduidingField(
        help_text=_("Maximaal toegelaten vertrouwelijkheidaanduiding (inclusief)."),
        blank=True,
    )

    objects = CatalogusAutorisatieManager()

    def natural_key(self):
        return (
            self.applicatie,
            self.catalogus,
            self.component,
        )

    class Meta:
        verbose_name = _("catalogus autorisatie")
        verbose_name_plural = _("catalogus autorisaties")
        unique_together = ("applicatie", "catalogus", "component")

    def __str__(self):
        return f"CatalogusAutorisatie voor {self.get_component_display()} en {self.catalogus} ({self.applicatie})"

    @classmethod
    def sync(cls, typen):
        """
        Synchronize the virtual Autorisaties for all Applicaties.
        Invoke this method whenever a ZaakType/InformatieObjectType/BesluitType
        is created to send the notifications to indicate that the Applicaties were updated.
        This is best called as part of `transaction.on_commit`.
        """
        from .utils import send_applicatie_changed_notification

        catalogi = [type.catalogus for type in typen]
        affected_catalogus_autorisaties = cls.objects.select_related(
            "applicatie"
        ).filter(catalogus__in=catalogi)

        # determine for which applicaties notificaties must be sent
        changed = {
            catalogus_autorisatie.applicatie
            for catalogus_autorisatie in affected_catalogus_autorisaties
        }

        for applicatie in changed:
            send_applicatie_changed_notification(applicatie)


class AutorisatieManager(models.Manager):
    def get_by_natural_key(self, applicatie, component, scopes):
        return self.get(applicatie=applicatie, component=component, scopes=scopes)


class Autorisatie(APIMixin, models.Model):
    applicatie = models.ForeignKey(
        Applicatie,
        on_delete=models.CASCADE,
        related_name="autorisaties",
        verbose_name=_("applicatie"),
    )
    component = models.CharField(
        _("component"),
        max_length=50,
        choices=ComponentTypes.choices,
        help_text=_("Component waarop autorisatie van toepassing is."),
    )
    scopes = ArrayField(
        models.CharField(max_length=100),
        verbose_name=_("scopes"),
        help_text=_("Komma-gescheiden lijst van scope labels."),
    )

    # ZRC exclusive
    zaaktype = models.ForeignKey(
        "catalogi.ZaakType",
        on_delete=models.CASCADE,
        related_name="autorisaties",
        help_text=_("het zaaktype waarop de autorisatie van toepassing is."),
        blank=True,
        null=True,
    )

    # DRC exclusive
    informatieobjecttype = models.ForeignKey(
        "catalogi.InformatieObjectType",
        on_delete=models.CASCADE,
        related_name="autorisaties",
        help_text=_(
            "het informatieobjecttype waarop de autorisatie van toepassing is."
        ),
        blank=True,
        null=True,
    )

    # BRC exclusive
    besluittype = models.ForeignKey(
        "catalogi.BesluitType",
        on_delete=models.CASCADE,
        related_name="autorisaties",
        help_text=_("het besluittype waarop de autorisatie van toepassing is."),
        blank=True,
        null=True,
    )

    # ZRC & DRC exclusive
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduidingField(
        help_text=_("Maximaal toegelaten vertrouwelijkheidaanduiding (inclusief)."),
        blank=True,
    )

    objects = AutorisatieManager()

    class Meta:
        ordering = ["pk"]
        verbose_name = _("autorisatie")
        verbose_name_plural = _("autorisaties")

    def natural_key(self):
        return (
            self.applicatie,
            self.component,
            self.scopes,
        )

    def satisfy_vertrouwelijkheid(self, vertrouwelijkheidaanduiding: str) -> bool:
        max_confid_level = VertrouwelijkheidsAanduiding.get_choice_order(
            self.max_vertrouwelijkheidaanduiding
        )
        provided_confid_level = VertrouwelijkheidsAanduiding.get_choice_order(
            vertrouwelijkheidaanduiding
        )

        if max_confid_level is None or provided_confid_level is None:
            raise ValueError("Invalid vertrouwelijkheidaanduiding value")

        return max_confid_level >= provided_confid_level
