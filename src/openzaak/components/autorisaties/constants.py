# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class RelatedTypeSelectionMethods(DjangoChoices):
    all_current = ChoiceItem("all_current", _("Alle huidige {verbose_name_plural}"))
    all_current_and_future = ChoiceItem(
        "all_current_and_future", _("Alle huidige en toekomstige {verbose_name_plural}")
    )
    manual_select = ChoiceItem("manual_select", _("Selecteer handmatig"))
