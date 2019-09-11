from django import forms

from .widgets import RelativeDeltaWidget


class RelativeDeltaField(forms.CharField):
    widget = RelativeDeltaWidget
    empty_strings_allowed = False

    def __init__(self, *args, **kwargs):
        assert "empty_value" not in kwargs, "empty_value may not be provided"
        kwargs["empty_value"] = None
        super().__init__(*args, **kwargs)
