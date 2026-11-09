# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import re

from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from django_loose_fk.drf import FKOrURLField, FKOrURLValidator
from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camel_to_underscore
from drf_spectacular.utils import extend_schema_field
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


# TODO performance: should this also use `vng_api_common.serializers.CacheMixin`?
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
            v
            for v in self.validators
            if type(v) != FKOrURLValidator  # noqa
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


def zoek_fields_schema(example: list | None = None) -> dict:
    """
    OpenAPI schema for the ``fields`` attribute of a ``_zoek`` operation.

    Returns a new dict on every call, because drf-spectacular merges the field
    metadata into the schema it is given.
    """
    schema = {
        "title": "Fields",
        "type": "array",
        "items": {"oneOf": [{"type": "string"}, {"type": "object"}]},
    }
    if example is not None:
        schema["example"] = example
    return schema


@extend_schema_field(zoek_fields_schema())
class ZoekFieldsSerializer(serializers.ListField):
    """
    Validate and parse response field selections for a resource.

    Accept a 'fields' array containing field names, '*' wildcards, or nested
    selections. Normalize names to snake_case, validate them against the
    response serializers, and merge repeated selections into a dictionary.
    """

    default_error_messages = {
        "invalid_selection": _(
            "Expected an array of field names or nested selections."
        ),
        "unknown_field": _("Unknown response field: {name}."),
        "not_nested": _("Field {name} does not support nested selection."),
    }
    parent_serializer_class = None

    def to_internal_value(self, data):
        """Validate the input list and convert it into a field selection dictionary"""
        data = super().to_internal_value(data)
        if self.parent_serializer_class is None:
            raise ImproperlyConfigured(
                "ZoekFieldsSerializer requires parent_serializer_class."
            )

        return self.parse_selection(data, self.parent_serializer_class())

    def parse_selection(self, entries, serializer):
        """Validate selections and build a dictionary for response field lookup

        ["uuid", {"zaaktype": ["omschrijving"]}]
        becomes {"uuid": None, "zaaktype": {"omschrijving": None}}
        """
        inclusions = getattr(serializer, "inclusion_serializers", {})
        serializer_cache = {}

        def get_nested_serializer(field, path, api_path):
            """Find the serializer used to validate fields inside a related object"""
            inclusion = inclusions.get(".".join(path))
            if inclusion:
                if inclusion not in serializer_cache:
                    serializer_cache[inclusion] = import_string(inclusion)()
                return serializer_cache[inclusion]
            if isinstance(field, serializers.Serializer):
                return field
            self.fail("not_nested", name=".".join(api_path))

        def parse(entries, serializer, path=(), api_path=()):
            """Check field names and parse nested selections"""
            if not isinstance(entries, list):
                self.fail("invalid_selection")

            selection = {}
            serializer_fields = serializer.fields

            for entry in entries:
                is_field_name = isinstance(entry, str)
                if is_field_name and entry == "*":
                    selection[entry] = None
                    continue

                if is_field_name:
                    fields = ((entry, None),)
                elif isinstance(entry, dict) and entry:
                    fields = entry.items()
                else:
                    self.fail("invalid_selection")

                for raw_name, children in fields:
                    name = camel_to_underscore(
                        raw_name, **api_settings.JSON_UNDERSCOREIZE
                    )
                    field = serializer_fields.get(name)
                    if is_field_name and field is not None and not field.write_only:
                        selection.setdefault(name, None)
                        continue

                    # Use camelCase field paths in validation errors
                    api_name = re.sub(
                        r"_([a-z])", lambda match: match.group(1).upper(), raw_name
                    )
                    child_api_path = (*api_path, api_name)
                    if field is None or field.write_only:
                        self.fail("unknown_field", name=".".join(child_api_path))

                    child_path = (*path, name)
                    child_serializer = get_nested_serializer(
                        field, child_path, child_api_path
                    )
                    nested = parse(
                        children, child_serializer, child_path, child_api_path
                    )
                    selection[name] = self.merge(selection.get(name) or {}, nested)
            return selection

        return parse(entries, serializer)

    @staticmethod
    def merge(left, right):
        """
        Merge selections into ``left``, keeping all requested nested fields.
        For example, {"status": {"url": None}} merged with
        {"status": {"omschrijving": None}} keeps both status fields.
        None selects a field directly and must not overwrite nested selections
        """
        for name, value in right.items():
            if isinstance(value, dict):
                left[name] = ZoekFieldsSerializer.merge(left.get(name) or {}, value)
            else:
                left.setdefault(name, value)
        return left
