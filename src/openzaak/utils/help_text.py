# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _


def mark_experimental(text):
    warning_msg = _(
        "Warning: this feature is experimental and not part of the API standard"
    )
    return "{} **{}**".format(text, warning_msg)
