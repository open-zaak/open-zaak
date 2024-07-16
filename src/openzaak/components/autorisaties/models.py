# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from vng_api_common.authorizations.models import Applicatie
from vng_api_common.constants import ComponentTypes
from vng_api_common.fields import VertrouwelijkheidsAanduidingField

COMPONENT_TO_MODEL = {
    ComponentTypes.zrc: "catalogi.ZaakType",
    ComponentTypes.drc: "catalogi.InformatieObjectType",
    ComponentTypes.brc: "catalogi.BesluitType",
}

COMPONENT_TO_FIELD = {
    ComponentTypes.zrc: "zaaktype",
    ComponentTypes.drc: "informatieobjecttype",
    ComponentTypes.brc: "besluittype",
}


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
        choices=ComponentTypes.choices,
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

    class Meta:
        verbose_name = _("catalogus autorisatie")
        verbose_name_plural = _("catalogus autorisaties")
        unique_together = ("applicatie", "catalogus", "component")

    def __str__(self):
        return f"CatalogusAutorisatie voor {self.get_component_display()} en {self.catalogus} ({self.applicatie})"
