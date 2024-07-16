# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db import models
from django.utils.translation import gettext_lazy as _


class RelatedTypeSelectionMethods(models.TextChoices):
    manual_select = "manual_select", _("Selecteer handmatig")
    select_catalogus = "select_catalogus", _("Selecteer catalogus")
