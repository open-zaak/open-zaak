# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django import forms
from django.core import validators

from .widgets import SplitRelativeDeltaWidget


class RelativeDeltaField(forms.CharField):
    widget = SplitRelativeDeltaWidget
    empty_strings_allowed = False
    empty_values = list(validators.EMPTY_VALUES) + ["P0D"]

    def __init__(self, *args, **kwargs):
        assert "empty_value" not in kwargs, "empty_value may not be provided"
        kwargs["empty_value"] = None
        super().__init__(*args, **kwargs)
