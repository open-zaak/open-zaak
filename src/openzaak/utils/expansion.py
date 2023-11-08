# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import logging
from typing import Dict, Generator, Iterator, List, Optional, Tuple, Type

from django.db import models
from django.utils.module_loading import import_string

from django_loose_fk.drf import FKOrURLField
from django_loose_fk.loaders import FetchError
from django_loose_fk.virtual_models import ProxyMixin
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from rest_framework.serializers import (
    BaseSerializer,
    Field,
    HyperlinkedRelatedField,
    ListSerializer,
    Serializer,
)
from rest_framework_inclusions.core import Error, InclusionLoader, sort_key
from rest_framework_inclusions.renderer import (
    InclusionJSONRenderer,
    get_allowed_paths,
    should_skip_inclusions,
)

from openzaak.utils.serializer_fields import FKOrServiceUrlField

logger = logging.getLogger(__name__)


class ExpandLoader(InclusionLoader):
    """
    ExpandLoader is hugely inspired by 'InclusionLoader' from 'djangorestframework-inclusions'

    Unlike InclusionLoader ExpandLoader keeps track on the parent object of the inclusion
    and the path to this inclusion.
    It helps to back track each inclusion to the root objects.
    Since this change affects most of the methods, some copy-pasting is involved here
    """

    response_expand_key = "_expand"

    def inclusions_dict(self, serializer: Serializer) -> dict:
        """
        The method is used by the renderer.

        :param serializer: serializer with 'instance'
        :return dictionary which maps parent urls and related inclusions

        The example of the inclusions with 'expand=zaaktype,status.statustype':
        {
          <zaak1.uuid>: {
            "zaaktype": {...},
            "status": {
               ...
               "_expand": {
                 "statustype": {...}
               }
            }
          }
        }
        """

        entries = self._inclusions((), serializer, serializer.instance)
        # FIXME make inclusions based on depth
        result = {}
        nested_inclusions = []
        for obj, inclusion_serializer, parent, path, many in entries:
            # TODO show nested objects
            print(
                "obj=",
                obj,
                "; inclusion_serializer=",
                inclusion_serializer,
                "; parent=",
                parent,
                "; path=",
                path,
                "; many=",
                many,
            )
            if len(path) > 1:
                nested_inclusions.append(
                    (obj, inclusion_serializer, parent, path, many)
                )
                continue

            # process 1-level inclusions
            request = serializer.context["request"]
            parent_url = parent.get_absolute_api_url(request=request)
            parent_results = result.setdefault(parent_url, {})

            # todo model_key = self.get_model_key(obj, inclusion_serializer) ?
            model_key = path[-1]

            data = inclusion_serializer(instance=obj, context=serializer.context).data
            if many:
                parent_results.setdefault(model_key, []).append(data)
            else:
                parent_results[model_key] = data

        # todo sort and process other inclusions
        # in-place sort of inclusions
        # for value in result.values():
        #     value.sort(key=sort_key)
        return result

    def _field_inclusions(
        self,
        path: Tuple[str, ...],
        field: Field,
        instance: models.Model,
        name: str,
        inclusion_serializers: Dict[str, str | Type[Serializer]],
    ) -> Iterator[
        Tuple[models.Model, Type[Serializer], models.Model, Tuple[str, ...], bool]
    ]:
        """
        change return of this generator from (obj, serializer_class) to
        (obj, serializer_class, parent_obj, path, many)
        """
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

        many = True if hasattr(field, "child_relation") else False
        for obj in self._some_related_field_inclusions(
            new_path, field, instance, inclusion_serializer
        ):
            yield obj, inclusion_serializer, instance, new_path, many
            # when we do inclusions in inclusions, we base path off our
            # parent object path, not the sub-field
            nested_path = (
                new_path if self.nested_inclusions_use_complete_path else new_path[:-1]
            )
            for entry in self._instance_inclusions(
                nested_path, inclusion_serializer(instance=object), obj
            ):
                yield entry

    def _some_related_field_inclusions(
        self,
        path: Tuple[str, ...],
        field: Field,
        instance: models.Model,
        inclusion_serializer: Type[Serializer],
    ) -> Iterator[models.Model]:
        """
        add handler for FKOrServiceUrlField fields
        """

        if self.allowed_paths is not None and path not in self.allowed_paths:
            return []

        if isinstance(field, FKOrServiceUrlField):
            return self._loose_fk_field_inclusions(
                path, field, instance, inclusion_serializer
            )

        return super()._some_related_field_inclusions(
            path, field, instance, inclusion_serializer
        )

    def _loose_fk_field_inclusions(
        self,
        path: Tuple[str],
        field: Field,
        instance: models.Model,
        inclusion_serializer: Type[Serializer],
    ) -> Iterator[models.Model]:
        obj = field.get_attribute(instance)
        if obj is None or obj.pk is None:
            return

        # TODO check if it's external link
        if self._has_been_seen(obj):
            return
        yield obj


class ExpandJSONRenderer(InclusionJSONRenderer, CamelCaseJSONRenderer):
    """
    Ensure that the InclusionJSONRenderer produces camelCase and properly loads loose fk
    objects
    """

    loader_class = ExpandLoader
    response_data_key = "results"

    def _render_inclusions(self, data, renderer_context):
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        # if we have an error, return data as-is
        if response is not None and response.status_code >= 400:
            return None

        render_data = data.copy()

        if render_data and "results" in render_data:
            serializer_data = render_data["results"]
        else:
            serializer_data = render_data

        serializer = getattr(serializer_data, "serializer", None)
        # if there is no serializer (like for a viewset action())
        # we just pass the data through as-is
        if serializer is None:
            return None

        # if it's a custom action, and the serializer has no inclusions,
        # return the normal response
        view = renderer_context.get("view")
        if view is not None and hasattr(view, "action"):
            if not view.action:
                logger.debug("Skipping inclusions for view that has no action")
                return None
            action = getattr(view, view.action)
            if should_skip_inclusions(action, serializer):
                logger.debug(
                    "Skipping inclusion machinery for custom action %r", action
                )
                return None

        request = renderer_context.get("request")

        inclusion_loader = self.loader_class(get_allowed_paths(request, view=view))
        inclusions = inclusion_loader.inclusions_dict(serializer)

        if isinstance(serializer_data, list):
            for record in serializer_data:
                if record["url"] in inclusions:
                    record["_expand"] = inclusions[record["url"]]

        if isinstance(serializer_data, dict):
            if serializer_data["url"] in inclusions:
                serializer_data["_expand"] = inclusions[serializer_data["url"]]

        return render_data


def get_expand_options_for_serializer(
    serializer_class: Type[Serializer],
) -> List[tuple]:
    choices = [(opt, opt,) for opt in serializer_class.inclusion_serializers]
    return choices
