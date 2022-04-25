# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from typing import List, Optional

from django.utils.module_loading import import_string

from django_loose_fk.drf import FKOrURLField
from django_loose_fk.loaders import FetchError
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from rest_framework.serializers import HyperlinkedRelatedField, Serializer
from rest_framework_inclusions.core import InclusionLoader as _InclusionLoader, sort_key
from rest_framework_inclusions.renderer import (
    InclusionJSONRenderer as _InclusionJSONRenderer,
)

from openzaak.utils.serializer_fields import (
    LooseFKHyperlinkedIdentityField,
    LooseFKHyperlinkedRelatedField,
)


def get_inclusion_key(serializer):
    return serializer.Meta.model._meta.label.lower().replace(".", ":")


class InclusionLoader(_InclusionLoader):
    nested_inclusions_use_parent = False

    def get_model_key(self, obj, serializer):
        return get_inclusion_key(serializer)

    def inclusions_dict(self, serializer):
        entries = self._inclusions((), serializer, serializer.instance)
        result = {}
        for obj, inclusion_serializer in entries:
            model_key = self.get_model_key(obj, inclusion_serializer)

            # In case of external resources
            if hasattr(obj, "_initial_data"):
                data = obj._initial_data
            else:
                data = inclusion_serializer(
                    instance=obj, context={"request": serializer.context.get("request")}
                ).data
            result.setdefault(model_key, []).append(data)
        # in-place sort of inclusions
        for value in result.values():
            value.sort(key=sort_key)
        return result

    def _some_related_field_inclusions(
        self, path, field, instance, inclusion_serializer
    ):
        if self.allowed_paths is not None and path not in self.allowed_paths:
            return []

        # Properly include loose fk fields
        if (
            isinstance(field, FKOrURLField)
            or isinstance(field, LooseFKHyperlinkedRelatedField)
            or isinstance(field, LooseFKHyperlinkedIdentityField)
        ):
            return self._loose_fk_field_inclusions(
                path, field, instance, inclusion_serializer
            )
        elif isinstance(field, HyperlinkedRelatedField):
            return self._primary_key_related_field_inclusions(
                path, field, instance, inclusion_serializer
            )
        return super()._some_related_field_inclusions(
            path, field, instance, inclusion_serializer
        )

    def _loose_fk_field_inclusions(self, path, field, instance, inclusion_serializer):
        value = field.get_attribute(instance)
        # In case it's an external resource
        if isinstance(value, str) or hasattr(value, "_initial_data"):
            try:
                yield getattr(instance, field.field_name)  # ._initial_data
            except FetchError:  # Something failed during fetching, ignore this instance
                return []
        else:
            for entry in self._primary_key_related_field_inclusions(
                path, field, instance, inclusion_serializer
            ):
                yield entry


class InclusionJSONRenderer(_InclusionJSONRenderer, CamelCaseJSONRenderer):
    """
    Ensure that the InclusionJSONRenderer produces camelCase and properly loads loose fk
    objects
    """

    loader_class = InclusionLoader


def get_include_options_for_serializer(
    dotted_path: str,
    serializer_class: Serializer,
    result: Optional[List[tuple]] = None,
    namespacing: bool = False,
    _seen: Optional[List[Serializer]] = None,
) -> List[tuple]:
    """
    Determine the possible options for the `include` query parameter given a serializer
    """
    if not result:
        result = []

    if not _seen:
        _seen = []

    if not hasattr(serializer_class, "inclusion_serializers"):
        return []

    # First add all the include options for the current serializers
    for field, inclusion_serializer in serializer_class.inclusion_serializers.items():
        serializer = import_string(inclusion_serializer)
        if namespacing:  # Namespace by component name
            key = get_inclusion_key(serializer)
        else:
            key = f"{dotted_path}.{field}" if dotted_path else field

        if f"{field}:{inclusion_serializer}" not in _seen:
            _seen.append(f"{field}:{inclusion_serializer}")
            result.append((key, serializer))

    # Add all the nested include options
    for field, inclusion_serializer in serializer_class.inclusion_serializers.items():
        if inclusion_serializer not in _seen:
            _seen.append(inclusion_serializer)
            serializer = import_string(inclusion_serializer)
            result = result + get_include_options_for_serializer(
                field, serializer, [], namespacing=namespacing, _seen=_seen
            )
    return result
