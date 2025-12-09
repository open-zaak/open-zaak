# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from typing import Any, Optional, Union

from django.contrib.admin.widgets import AdminFileWidget
from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile
from django.db.models.fields.files import FieldFile

from privates.widgets import PrivateFileWidget as _PrivateFileWidget

from .storage import documenten_storage


class PrivateFileWidget(_PrivateFileWidget):
    def get_display_value(
        self, value: Optional[Union[InMemoryUploadedFile, FieldFile]]
    ):
        if not value or not hasattr(value, "instance"):
            return super().get_display_value(value)

        instance = value.instance
        return instance.bestandsnaam or super().get_display_value(value)


class AzureFileWidget(AdminFileWidget):
    """
    Widget to display files stored in Azure
    """

    template_name = "admin/widgets/clearable_private_file_input.html"

    def __init__(self, *args, **kwargs):
        self.url_name = kwargs.pop("url_name")
        self.download_allowed = kwargs.pop("download_allowed")
        super().__init__(*args, **kwargs)

    def get_context(
        self,
        name: str,
        value: FieldFile | UploadedFile | None,
        attrs: dict[str, Any] | None,
    ):
        """
        Return value-related substitutions.
        """
        context = super().get_context(name, value, attrs)  # type: ignore
        if self.is_initial(value):  # type: ignore
            if self.download_allowed:
                assert isinstance(value, FieldFile)
                context["url"] = documenten_storage.url(value.name)
                context["download_allowed"] = True
            else:
                context["url"] = ""
                context["download_allowed"] = False
            context["display_value"] = self.get_display_value(value)
        return context

    def get_display_value(self, value: Union[InMemoryUploadedFile, FieldFile]) -> str:
        # TODO this currently ignores `bestandsnaam` as attachment filename
        return value.path
