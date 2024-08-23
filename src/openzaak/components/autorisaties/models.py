# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from vng_api_common.authorizations.models import Applicatie
from vng_api_common.constants import ComponentTypes
from vng_api_common.fields import VertrouwelijkheidsAanduidingField

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
