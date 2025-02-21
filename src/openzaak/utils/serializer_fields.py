# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import gettext_lazy as _

from django_loose_fk.drf import FKOrURLField, FKOrURLValidator
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


class FKOrServiceUrlValidator(FKOrURLValidator):
    # TODO: move this to validators.py
    RESOLVED_INSTANCE_CONTEXT_KEY = "_resolved_instance"

    def __call__(self, url: str, serializer_field):
        # ⚡️ the field context is the same as the serializer context, so once one
        # validator subclassing `FKOrServiceUrlValidator` has resolved the instance, we
        # can use the cached result to avoid repeating the same queries/network calls
        # over and over again.
        context_key = self.get_context_cache_key(serializer_field)
        if serializer_field.context.get(context_key) is not None:
            return

        try:
            super().__call__(url, serializer_field)
        except ValueError as exc:
            raise serializers.ValidationError(
                _("The service for this url is unknown"), code="unknown-service"
            ) from exc

        # if there are no validation errors, the parent class has added the resolver
        # to the serializer context - we can use this to resolve the object and cache
        # it for other validators to skip some DB queries
        resolver = serializer_field.context["resolver"]
        host = serializer_field.context["request"].get_host()
        resolved_instance = resolver.resolve(host, url)
        serializer_field.context[context_key] = resolved_instance

    @staticmethod
    def get_context_cache_key(field):
        field_names = [field.field_name]
        while (field := field.parent) and field.field_name:
            field_names.append(field.field_name)
        names = "__".join(field_names)
        return f"_resolved_{names}"


class FKOrServiceUrlField(FKOrURLField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # replace FKOrURLValidator with FKOrServiceUrlValidator
        self.validators = [
            v for v in self.validators if type(v) != FKOrURLValidator  # noqa
        ]
        self.validators += [FKOrServiceUrlValidator()]

    def _get_model_and_field(self) -> tuple:
        # find parent serializer, if fields with nesting are used (like lists or dicts)
        parent = self.parent
        while hasattr(parent, "parent") and not isinstance(
            parent, serializers.Serializer
        ):
            parent = parent.parent

        model_class = parent.Meta.model

        source = self.source or self.parent.source
        # remove filters if present
        source = source.split("__")[0]
        model_field = model_class._meta.get_field(source)
        return model_class, model_field
