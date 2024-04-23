# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _


def mark_experimental(text):
    return _("**EXPERIMENTEEL** {}").format(text)
