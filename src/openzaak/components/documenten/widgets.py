# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import Optional, Union

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models.fields.files import FieldFile

from privates.widgets import PrivateFileWidget as _PrivateFileWidget


class PrivateFileWidget(_PrivateFileWidget):
    def get_display_value(
        self, value: Optional[Union[InMemoryUploadedFile, FieldFile]]
    ):
        if not value or not hasattr(value, "instance"):
            return super().get_display_value(value)

        instance = value.instance
        return instance.bestandsnaam or super().get_display_value(value)
