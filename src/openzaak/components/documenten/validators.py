# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date
from os.path import splitext

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .constants import (
    MAX_INHOUD_FILENAME_LENGTH,
    MAX_UPLOAD_INHOUD_FILENAME_LENGTH,
    Statussen,
)


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


def validate_inhoud_filename(inhoud):
    """
    Validate the uploaded inhoud filename length.
    Reject filenames over 255 characters and shorten names over 247,
    keeping the extension and leaving room for Django's 8-character
    suffix when a file with the same name already exists.
    """

    # Only validate files that are present and haven’t been saved yet
    if not inhoud or getattr(inhoud, "_committed", False):
        return

    filename_length = len(inhoud.name)

    if filename_length > MAX_INHOUD_FILENAME_LENGTH:
        raise ValidationError(
            _(
                "De bestandsnaam van de inhoud mag niet langer zijn dan 255 tekens, inclusief de extensie."
            )
        )

    # Django adds eight characters when resolving a filename collision
    # Ensure that the filename has room for eight characters
    if filename_length > MAX_UPLOAD_INHOUD_FILENAME_LENGTH:
        name, extension = splitext(inhoud.name)
        # Shorten only the name, keeping the extension and space for Django's 8-character suffix
        max_name_length = MAX_UPLOAD_INHOUD_FILENAME_LENGTH - len(extension)
        inhoud.name = name[:max_name_length] + extension
