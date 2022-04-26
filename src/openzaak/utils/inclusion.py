# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from typing import List, Optional

from django.utils.module_loading import import_string

from django_loose_fk.drf import FKOrURLField
from django_loose_fk.loaders import FetchError
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from rest_framework.serializers import (
    BaseSerializer,
    HyperlinkedRelatedField,
    Serializer,
)
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

    def _instance_inclusions(
        self, path, serializer, instance, inclusion_serializers=None
    ):
        # Use inclusion serializers derived from parent serializer
        inclusion_serializers = inclusion_serializers or getattr(
            serializer, "inclusion_serializers", {}
        )
        for name, field in serializer.fields.items():
            for entry in self._field_inclusions(
                path, field, instance, name, inclusion_serializers
            ):
                yield entry

    def _field_inclusions(self, path, field, instance, name, inclusion_serializers):
        # if this turns out to be None, we don't want to do a thing
        if instance is None:
            return
        new_path = path + (name,)
        if isinstance(field, BaseSerializer):
            for entry in self._sub_serializer_inclusions(new_path, field, instance):
                yield entry
            return
        inclusion_serializer = inclusion_serializers.get(name)
        if inclusion_serializer is None:
            return
        if isinstance(inclusion_serializer, str):
            inclusion_serializer = import_string(inclusion_serializer)
        for obj in self._some_related_field_inclusions(
            new_path, field, instance, inclusion_serializer
        ):
            yield obj, inclusion_serializer
            # when we do inclusions in inclusions, we base path off our
            # parent object path, not the sub-field

            # TODO option to derive serializers from parent serializer, instead of child
            # serializer
            nested_serializers = {
                field_name[len(name) + 1 :]: serializer
                for field_name, serializer in inclusion_serializers.items()
                if field_name.startswith(name)
            }

            nested_path = (
                new_path[:-1] if self.nested_inclusions_use_parent else new_path
            )
            for entry in self._instance_inclusions(
                nested_path,
                inclusion_serializer(instance=object),
                obj,
                inclusion_serializers=nested_serializers,
            ):
                yield entry

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
    serializer_class: Serializer, namespacing: Optional[bool] = False
) -> List[tuple]:
    if namespacing:
        choices = []
        for opt in serializer_class.inclusion_serializers.values():
            key = get_inclusion_key(import_string(opt))
            choices.append((key, key,))
    else:
        choices = [(opt, opt,) for opt in serializer_class.inclusion_serializers]
    choices.append(("*", "*",))
    return choices
