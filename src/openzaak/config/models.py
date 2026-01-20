# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.db import models
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from vng_api_common.constants import ComponentTypes

from openzaak.utils.constants import COMPONENT_MAPPING


class InternalService(models.Model):
    api_type = models.CharField(
        _("API type"), max_length=50, choices=ComponentTypes.choices, unique=True
    )
    enabled = models.BooleanField(
        _("enabled"),
        default=True,
        help_text=_("Indicates if the API is enabled in Open Zaak."),
    )

    class Meta:
        verbose_name = _("Internal service")
        verbose_name_plural = _("Internal services")

    def __str__(self):
        return self.get_api_type_display()

    @property
    def component(self) -> str:
        for component, api_type in COMPONENT_MAPPING.items():
            if api_type == self.api_type:
                return component
        raise ValueError(f"Unknown component for api_type '{self.api_type}'")


class FeatureFlags(SingletonModel):
    """
    Configure global feature flags for the system.

    Feature flags are usually booleans indicating if some feature is enabled/disabled.
    They can have side-effects that make the APIs operate in a non-standards compliant
    way, so think carefully about default values.
    """

    allow_unpublished_typen = models.BooleanField(
        _("allow concept *typen"),
        default=False,
        help_text=_(
            "Normally, a type must be published before an object of that type (ZAAK, "
            "INFORMATIEOBJECT, BESLUIT) can be created from it. Enabling this flag "
            "bypasses this check. This is intended to support development - do not "
            "enable this in production."
        ),
    )

    class Meta:
        verbose_name = _("feature flags")

    def __str__(self):
        return force_str(self._meta.verbose_name)
