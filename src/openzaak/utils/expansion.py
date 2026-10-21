# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from typing import Dict, Iterable, Iterator, List, Optional, Tuple, Type, Union

from django.db import models
from django.utils.module_loading import import_string

import structlog
from django_loose_fk.loaders import FetchError
from django_loose_fk.virtual_models import ProxyMixin
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camel_to_underscore
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.serializers import BaseSerializer, Field, Serializer
from rest_framework_inclusions.core import InclusionLoader
from rest_framework_inclusions.renderer import (
    InclusionJSONRenderer,
    get_allowed_paths,
    should_skip_inclusions,
)

from openzaak.utils.serializer_fields import FKOrServiceUrlField

logger = structlog.stdlib.get_logger(__name__)

EXPAND_KEY = "_expand"
EXPAND_QUERY_PARAM = "expand"


class InclusionNode:
    """
    very simple implementation of the tree to display inclusions
    """

    def __init__(
        self,
        id: str,
        value: dict,
        label: str,
        many: bool,
        parent: "InclusionNode" = None,
    ):
        self.id = id
        self.value = value
        self.label = label
        self.many = many
        self.parent = parent
        self._children = []

        if self.parent:
            self.parent.add_child(self)

    def __str__(self):
        return f"{self.label}: {self.id}"

    def add_child(self, node: "InclusionNode"):
        self._children.append(node)

    def display_children(self) -> dict:
        """
        return dict where children are grouped by their label
        """
        results = {}
        for child in self._children:
            child_result = child.display()
            if child.many:
                results.setdefault(child.label, []).append(child_result)
            else:
                results[child.label] = child_result
        return results

    def display(self) -> dict:
        data = self.value.copy()
        if self._children:
            data[EXPAND_KEY] = self.display_children()
        return data

    def has_child(self, id) -> bool:
        return any(child.id == id for child in self._children)


class InclusionTree:
    """
    strictly speaking it's not a tree but a collection of nodes
    It's a little helper class to display nested inclusions
    """

    def __init__(self):
        self._nodes = []

    def add_node(
        self, id: str, value: dict, label: str, many: bool, parent_id: str = None
    ) -> None:
        if not parent_id:
            node = InclusionNode(id, value, label, many)
            self._nodes.append(node)
            return

        parent_nodes = [
            n for n in self._nodes if n.id == parent_id and not n.has_child(id)
        ]
        for parent_node in parent_nodes:
            node = InclusionNode(id, value, label, many, parent=parent_node)
            self._nodes.append(node)

    def display_tree(self) -> dict:
        result = {}
        root_nodes = [n for n in self._nodes if n.parent is None]

        for node in root_nodes:
            result[node.id] = node.display_children()
        return result


class ExpandLoader(InclusionLoader):
    """
    ExpandLoader is hugely inspired by 'InclusionLoader' from 'djangorestframework-inclusions'

    Unlike InclusionLoader ExpandLoader keeps track of the parent object of the inclusion
    and the path to this inclusion.
    It helps to back track each inclusion to the root objects.
    Since this change affects most of the methods, some copy-pasting is involved here
    """

    selected_fields: dict | None = None  # Use for FieldsMixin

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._seen_external: Dict[str, ProxyMixin] = {}
        self._seen_local: dict[tuple[type[Serializer], int], models.Model] = {}
        self._serialized: dict[tuple[type[Serializer], int, str], dict] = {}

    def inclusions_dict(self, serializer: Serializer) -> dict:
        """
        The method is used by the renderer.

        :param serializer: serializer with 'instance'
        :return dictionary which maps parent urls and related inclusions

        The example of the inclusions with 'expand=zaaktype,status,status.statustype':
        {
          <zaak1.url>: {
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

        tree = InclusionTree()
        request = serializer.context["request"]

        # add parent nodes to the tree
        instances = (
            serializer.instance
            if isinstance(serializer.instance, (list, models.QuerySet))
            else [serializer.instance]
        )
        for instance in instances:
            tree.add_node(
                id=instance.get_absolute_api_url(request=request),
                label="",
                value={},
                many=False,
            )

        entries = self._inclusions((), serializer, serializer.instance)

        self.selected_fields = getattr(
            serializer.context.get("view"), "_selected_fields", None
        )
        selections_by_path = {}

        for obj, inclusion_serializer, parent, path, many in entries:
            if isinstance(obj, ProxyMixin):
                data = obj._initial_data
            else:
                # Reuse the selection and cache key for every object at this path.
                if path not in selections_by_path:
                    fields = fields_at_path(self.selected_fields, path)
                    selections_by_path[path] = (fields, repr(fields))
                fields, selection_key = selections_by_path[path]
                cache_key = (inclusion_serializer, obj.pk, selection_key)
                if cache_key not in self._serialized:
                    child_serializer = inclusion_serializer(
                        instance=obj, context=serializer.context
                    )
                    if fields is not None:
                        limit_serializer_fields(child_serializer, fields)
                    self._serialized[cache_key] = child_serializer.data
                data = self._serialized[cache_key]
            tree.add_node(
                id=data["url"],
                value=data,
                label=path[-1],
                many=many,
                parent_id=parent.get_absolute_api_url(request=request),
            )

        result = tree.display_tree()
        return result

    def _instance_inclusions(
        self,
        path: Tuple[str, ...],
        serializer: Serializer,
        instance: models.Model,
        inclusion_serializers: Optional[dict] = None,
    ):
        """
        add parameter 'inclusion_serializers'
        """
        inclusion_serializers = inclusion_serializers or getattr(
            serializer, "inclusion_serializers", {}
        )

        # Keep only the fields requested for the resource at this path
        fields = fields_at_path(self.selected_fields, path)
        if fields is not None:
            limit_serializer_fields(serializer, fields)

        for name, field in serializer.fields.items():
            yield from self._field_inclusions(
                path, field, instance, name, inclusion_serializers
            )

    def _field_inclusions(
        self,
        path: Tuple[str, ...],
        field: Field,
        instance: models.Model,
        name: str,
        inclusion_serializers: Dict[str, Union[str, Type[Serializer]]],
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
            yield from self._sub_serializer_inclusions(new_path, field, instance)
            return
        inclusion_serializer = inclusion_serializers.get(".".join(new_path))
        if inclusion_serializer is None:
            return
        if isinstance(inclusion_serializer, str):
            inclusion_serializer = import_string(inclusion_serializer)

        many = hasattr(field, "child_relation")

        for obj in self._some_related_field_inclusions(
            new_path, field, instance, inclusion_serializer
        ):
            yield obj, inclusion_serializer, instance, new_path, many
            # when we do inclusions in inclusions, we base path off our
            # parent object path, not the sub-field
            yield from self._instance_inclusions(
                new_path,
                inclusion_serializer(instance=object),
                obj,
                inclusion_serializers,
            )

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
        path: Tuple[str, ...],
        field: Field,
        instance: models.Model,
        inclusion_serializer: Type[Serializer],
    ) -> Iterator[models.Model]:
        """
        handler for loose-fk-field

        For a local target, peek at the raw FK id first (a plain attribute,
        never a query) so a target already seen for another parent object can
        be reused without hitting the database again. This mirrors the
        existing ``_seen_external`` cache below, which only covers external
        (URL-based) targets.
        """
        model_field = field._get_model_and_field()[1]
        url_value = getattr(instance, model_field.url_field)

        if not url_value:
            local_pk = getattr(instance, f"{model_field.fk_field}_id", None)
            if local_pk is not None:
                cache_key = (inclusion_serializer, local_pk)
                if (
                    cache_key in self._seen_local
                    and model_field.fk_field not in instance._state.fields_cache
                ):
                    yield self._seen_local[cache_key]
                    return

        obj = field.get_attribute(instance)
        if hasattr(field, "get_inclusion_instance"):
            obj = field.get_inclusion_instance(obj)

        if obj is None:
            return

        # external
        if isinstance(obj, str):
            # check in cache
            if obj in self._seen_external:
                yield self._seen_external[obj]

            else:
                try:
                    # model field descriptor uses loader for external urls
                    instance = getattr(instance, field.field_name)
                except FetchError:
                    return
                else:
                    self._seen_external[obj] = instance
                    yield instance

        # local
        else:
            if obj.pk is not None:
                self._seen_local[(inclusion_serializer, obj.pk)] = obj
            yield obj

    def _has_been_seen(self, obj: models.Model) -> bool:
        """
        we don't deduplicate objects here
        """
        return False

    def _sub_serializer_inclusions(self, path, field, instance):
        """
        added condition for loose-fk chained instances (like zaaktype.gerelateerde_zaaktypen):
        stop and don't do chained requests for now
        """
        if isinstance(instance, ProxyMixin):
            return []

        return super()._sub_serializer_inclusions(path, field, instance)


class ExpandJSONRenderer(InclusionJSONRenderer, CamelCaseJSONRenderer):
    """
    Ensure that the InclusionJSONRenderer produces camelCase and properly loads loose fk
    objects
    """

    loader_class = ExpandLoader

    def _render_inclusions(self, data, renderer_context):
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        # if we have an error, return data as-is
        if response is not None and response.status_code >= 400:
            return None

        if not data:
            return None

        render_data = data.copy()

        if render_data and "results" in render_data:
            serializer_data = render_data["results"]
            serializer = getattr(serializer_data, "serializer", None)
        else:
            serializer_data = render_data
            serializer = getattr(data, "serializer", None)

        # if there is no serializer (like for a viewset action())
        # we just pass the data through as-is
        if serializer is None:
            return None

        # if it's a custom action, and the serializer has no inclusions,
        # return the normal response
        view = renderer_context.get("view")
        if view is not None and hasattr(view, "action"):
            if not view.action:
                logger.debug("skipping_inclusions_no_action")
                return None
            action = getattr(view, view.action)
            if should_skip_inclusions(action, serializer):
                logger.debug(
                    "skipping_inclusion_machinery_for_custom_action", action=action
                )
                return None

        request: Request | None = renderer_context.get("request")
        assert request

        has_expand = getattr(view, "has_expand", lambda request: False)
        get_inclusions = getattr(view, "get_requested_inclusions", lambda request: ())

        if has_expand(request) or get_inclusions(request):
            inclusion_loader = self.loader_class(get_allowed_paths(request, view=view))
            inclusions = inclusion_loader.inclusions_dict(serializer)

            if isinstance(serializer_data, list):
                for record in serializer_data:
                    if record["url"] in inclusions:
                        record[EXPAND_KEY] = inclusions[record["url"]]

            if isinstance(serializer_data, dict):
                if inclusions.get(serializer_data["url"]):
                    serializer_data[EXPAND_KEY] = inclusions[serializer_data["url"]]
        else:
            # Always include the empty `_expand` attribute
            if isinstance(serializer_data, list):
                for record in serializer_data:
                    record[EXPAND_KEY] = {}

            if isinstance(serializer_data, dict):
                serializer_data[EXPAND_KEY] = {}

        # Skip field filtering unless this is a _zoek request with selected fields
        has_fields = getattr(view, "has_fields", lambda request: False)
        selected_fields = getattr(view, "_selected_fields", None)
        if not has_fields(request) or selected_fields is None:
            return render_data

        def explicit_paths(entries, path=()):
            for entry in entries:
                if isinstance(entry, str):
                    yield (
                        *path,
                        camel_to_underscore(entry, **api_settings.JSON_UNDERSCOREIZE),
                    )
                elif isinstance(entry, dict):
                    for name, children in entry.items():
                        name = camel_to_underscore(
                            name, **api_settings.JSON_UNDERSCOREIZE
                        )
                        yield from explicit_paths(children, (*path, name))

        explicit_fields = set(explicit_paths(view.request.data["fields"]))

        def filter_selected_fields(value, selected_fields, path=()):
            if selected_fields is None or not isinstance(value, (dict, list)):
                return value
            if isinstance(value, list):
                return [
                    filter_selected_fields(item, selected_fields, path)
                    for item in value
                ]

            select_all = "*" in selected_fields
            expanded_fields = value.get(EXPAND_KEY, {})
            result = value.copy() if select_all else {}
            result.pop(EXPAND_KEY, None)

            # Include relation URLs only when explicitly selected at this path
            result.update(
                {
                    name: filter_selected_fields(value[name], children, (*path, name))
                    for name, children in selected_fields.items()
                    if name in value
                    and (
                        name not in expanded_fields
                        or select_all
                        or (*path, name) in explicit_fields
                    )
                }
            )

            # Apply each expansion's own field selection
            filtered_expansions = {
                name: filter_selected_fields(
                    item, selected_fields.get(name), (*path, name)
                )
                for name, item in expanded_fields.items()
                if selected_fields.get(name) is not None
            }

            if filtered_expansions or (
                select_all and EXPAND_KEY in value and not expanded_fields
            ):
                result[EXPAND_KEY] = filtered_expansions
            return result

        if "results" in render_data:
            render_data["results"] = filter_selected_fields(
                render_data["results"], selected_fields
            )
            return render_data
        return filter_selected_fields(render_data, selected_fields)


def get_expand_options_for_serializer(
    serializer_class: Type[Serializer],
) -> List[tuple]:
    choices = [(opt, opt) for opt in serializer_class.inclusion_serializers]
    return choices


def fields_at_path(selected_fields: dict | None, path: Iterable[str]) -> dict | None:
    """
    Return the fields selected at this path, or None if it is not expanded
    """
    for name in path:
        if selected_fields is None:
            return None
        selected_fields = selected_fields.get(name)
    return selected_fields


def limit_serializer_fields(
    serializer: BaseSerializer, selected_fields: dict
) -> BaseSerializer:
    """
    Keep only selected fields, including nested fields and any '*' selections
    """
    if isinstance(serializer, serializers.ListSerializer):
        serializer = serializer.child
    select_all = "*" in selected_fields  # avoid repeated call in the loop

    for name, field in list(serializer.fields.items()):
        if not select_all and name not in selected_fields and name != "url":
            del serializer.fields[name]
            continue
        children = selected_fields.get(name)
        if children is not None and isinstance(field, serializers.BaseSerializer):
            limit_serializer_fields(field, children)
    return serializer
