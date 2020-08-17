# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_better_admin_arrayfield.models.fields import ArrayField
from vng_api_common.decorators import field_default
from vng_api_common.models import ClientConfig


@field_default("api_root", "https://selectielijst.openzaak.nl/api/v1/")
class ReferentieLijstConfig(ClientConfig):
    class Meta:
        verbose_name = _("Selectielijstconfiguratie")

    allowed_years = ArrayField(
        base_field=models.PositiveIntegerField(),
        help_text=_("De jaartallen waarvan er procestypen gebruikt mogen worden."),
        default=list,
    )
    default_year = models.PositiveIntegerField(
        help_text=_(
            "Het jaartal dat standaard geselecteerd is bij het kiezen van "
            "een procestype bij een zaaktype."
        ),
        null=True,
    )
