# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class VervalRedenen(DjangoChoices):
    tijdelijk = ChoiceItem("tijdelijk", label=_("Besluit met tijdelijke werking"))
    ingetrokken_overheid = ChoiceItem(
        "ingetrokken_overheid", label=_("Besluit ingetrokken door overheid")
    )
    ingetrokken_belanghebbende = ChoiceItem(
        "ingetrokken_belanghebbende",
        label=_("Besluit ingetrokken o.v.v. belanghebbende"),
    )
