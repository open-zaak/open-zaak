# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_better_admin_arrayfield.models.fields import ArrayField
from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


class ReferentieLijstConfig(SingletonModel):
    service = models.ForeignKey(
        "zgw_consumers.Service",
        limit_choices_to={"api_type": APITypes.orc},
        verbose_name=_("Referentielijsten API service"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Selectielijstconfiguratie")

    allowed_years = ArrayField(
        base_field=models.PositiveIntegerField(),
        help_text=_("The years from which procestypen may be used."),
        default=list,
    )
    default_year = models.PositiveIntegerField(
        help_text=_(
            "The year that is selected by default when choosing a "
            "procestype for a zaaktype."
        ),
        null=True,
        default=2020,
    )
