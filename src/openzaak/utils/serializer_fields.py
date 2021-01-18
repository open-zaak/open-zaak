# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from vng_api_common.validators import URLValidator


class LengthValidationMixin:
    default_error_messages = {
        "max_length": _("Ensure this field has no more than {max_length} characters."),
        "min_length": _("Ensure this field has at least {min_length} characters."),
        "bad-url": "The URL {url} could not be fetched. Exception: {exc}",
        "invalid-resource": "Please provide a valid URL. Exception: {exc}",
    }

    def __init__(self, **kwargs):
        self.max_length = kwargs.pop("max_length", None)
        self.min_length = kwargs.pop("min_length", None)

        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if self.max_length and len(data) > self.max_length:
            self.fail("max_length", max_length=self.max_length, length=len(data))

        if self.min_length and len(data) < self.min_length:
            self.fail("min_length", max_length=self.min_length, length=len(data))

        # check if url is valid
        try:
            value = super().to_internal_value(data)
        except ValidationError as field_exc:
            # rewrite validation code to make it fit reference implementation
            # if url is not valid
            try:
                URLValidator()(data)
            except ValidationError as exc:
                self.fail("bad-url", url=data, exc=exc)

            # if the url is not bad -> then the problem is that it doesn't fit resource
            self.fail("invalid-resource", exc=field_exc)
        return value


class LengthHyperlinkedRelatedField(
    LengthValidationMixin, serializers.HyperlinkedRelatedField
):
    pass
