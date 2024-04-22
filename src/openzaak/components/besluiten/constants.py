# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db import models
from django.utils.translation import gettext_lazy as _


class VervalRedenen(models.TextChoices):
    tijdelijk = "tijdelijk", _("Besluit met tijdelijke werking")
    ingetrokken_overheid = (
        "ingetrokken_overheid",
        _("Besluit ingetrokken door overheid"),
    )
    ingetrokken_belanghebbende = (
        "ingetrokken_belanghebbende",
        _("Besluit ingetrokken o.v.v. belanghebbende"),
    )
