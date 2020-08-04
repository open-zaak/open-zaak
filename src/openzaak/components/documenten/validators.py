# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from .constants import Statussen


def validate_status(status: str = None, ontvangstdatum: date = None, instance=None):
    """
    Validate that certain status values are not used when an ontvangstdatum is
    provided.
    """
    if ontvangstdatum is None and instance is not None:
        ontvangstdatum = instance.ontvangstdatum

    if status is None and instance is not None:
        status = instance.status

    # if it's still empty, all statusses are allowed
    if ontvangstdatum is None:
        return

    # it is an optional field...
    if not status:
        return

    invalid_statuses = Statussen.invalid_for_received()
    if status in invalid_statuses:
        values = ", ".join(invalid_statuses)
        raise ValidationError(
            {
                "status": ValidationError(
                    _(
                        "De statuswaarden `{values}` zijn niet van toepassing "
                        "op ontvangen documenten."
                    ).format(values=values),
                    code="invalid_for_received",
                )
            }
        )
