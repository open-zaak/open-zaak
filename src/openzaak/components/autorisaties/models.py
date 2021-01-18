# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from collections import defaultdict

from django.apps import apps
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import ComponentTypes
from vng_api_common.fields import VertrouwelijkheidsAanduidingField

from openzaak.utils import build_absolute_url

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


class AutorisatieSpec(models.Model):
    """
    Specification for Autorisatie to install.

    If a spec exists, it will be applied when a ZaakType, InformatieObjectType
    or BesluitType is created.
    """

    applicatie = models.ForeignKey(
        Applicatie,
        on_delete=models.CASCADE,
        related_name="autorisatie_specs",
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
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduidingField(
        help_text=_("Maximaal toegelaten vertrouwelijkheidaanduiding (inclusief)."),
        blank=True,
    )

    class Meta:
        verbose_name = _("autorisatiespec")
        verbose_name_plural = _("autorisatiespecs")
        # since the spec implicates this config is valid for _all_ zaaktypen/
        # informatieobjecttypen/besluittypen, the scopes/VA are constant for
        # these. The exact *type is implied by the component choice, so we need
        # a unique constraint on applicatie + component
        unique_together = ("applicatie", "component")

    def __str__(self):
        return _("{component} autorisatiespec voor {app}").format(
            component=self.get_component_display(), app=self.applicatie
        )

    @classmethod
    def sync(cls):
        """
        Synchronize the Autorisaties for all Applicaties.

        Invoke this method whenever a ZaakType/InformatieObjectType/BesluitType
        is created to set up the appropriate Autorisatie objects. This is best
        called as part of `transaction.on_commit`.
        """
        from .utils import send_applicatie_changed_notification

        qs = cls.objects.select_related("applicatie").prefetch_related(
            "applicatie__autorisaties"
        )

        to_delete = []
        to_keep = []
        to_add = []

        for spec in qs:
            existing_autorisaties = [
                autorisatie
                for autorisatie in spec.applicatie.autorisaties.all()
                if autorisatie.component == spec.component
            ]

            for autorisatie in existing_autorisaties:
                # schedule for deletion if existing objects differ from the spec
                if (
                    autorisatie.max_vertrouwelijkheidaanduiding
                    != spec.max_vertrouwelijkheidaanduiding
                ):
                    to_delete.append(autorisatie)
                    continue

                if set(autorisatie.scopes) != set(spec.scopes):
                    to_delete.append(autorisatie)
                    continue

                to_keep.append(autorisatie)

            TypeModel = apps.get_model(COMPONENT_TO_MODEL[spec.component])
            field = COMPONENT_TO_FIELD[spec.component]

            for obj in TypeModel.objects.all():
                url = build_absolute_url(obj.get_absolute_api_url())

                autorisatie = Autorisatie(
                    applicatie=spec.applicatie,
                    component=spec.component,
                    scopes=spec.scopes,
                    max_vertrouwelijkheidaanduiding=spec.max_vertrouwelijkheidaanduiding,
                    **{field: url}
                )
                to_add.append(autorisatie)

        Autorisatie.objects.filter(
            pk__in=[autorisatie.pk for autorisatie in to_delete]
        ).delete()

        # de-duplicate - whatever is in to_keep should not be added again
        existing_urls = defaultdict(list)
        for autorisatie in to_keep:
            if autorisatie.component not in COMPONENT_TO_FIELD:
                continue
            url = getattr(autorisatie, COMPONENT_TO_FIELD[autorisatie.component])
            existing_urls[autorisatie.component].append(url)

        _to_add = []
        for autorisatie in to_add:
            if autorisatie.component not in COMPONENT_TO_FIELD:
                continue
            url = getattr(autorisatie, COMPONENT_TO_FIELD[autorisatie.component])
            if url in existing_urls[autorisatie.component]:
                continue
            _to_add.append(autorisatie)

        # created the de-duplicated, missing autorisaties
        Autorisatie.objects.bulk_create(_to_add)

        # determine which notifications to send
        changed = {autorisatie.applicatie for autorisatie in (to_delete + _to_add)}
        for applicatie in changed:
            send_applicatie_changed_notification(applicatie)
