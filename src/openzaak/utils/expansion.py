# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from functools import cache
from typing import Dict, Iterator, List, Optional, Tuple, Type, Union

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import Prefetch
from django.utils.module_loading import import_string

import structlog
from django_loose_fk.loaders import FetchError
from django_loose_fk.virtual_models import ProxyMixin
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
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
        selected_fields = getattr(
            serializer.context.get("view"), "_selected_fields", None
        )
        self.selected_fields = selected_fields

        for obj, inclusion_serializer, parent, path, many in entries:
            if isinstance(obj, ProxyMixin):
                data = obj._initial_data
            else:
                fields = SelectedFieldsExpansion.fields_at_path(selected_fields, path)
                cache_key = (inclusion_serializer, obj.pk, repr(fields))
                if cache_key not in self._serialized:
                    child_serializer = inclusion_serializer(
                        instance=obj, context=serializer.context
                    )
                    if fields is not None:
                        SelectedFieldsExpansion.limit_serializer_fields(
                            child_serializer, fields
                        )
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
        selected_fields = SelectedFieldsExpansion.fields_at_path(
            getattr(self, "selected_fields", None), path
        )
        if selected_fields is not None:
            SelectedFieldsExpansion.limit_serializer_fields(serializer, selected_fields)
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
        expanded = self._get_expanded_data(data, renderer_context)
        context = renderer_context or {}
        view = context.get("view")
        selected_fields = getattr(view, "_selected_fields", None)
        if (
            expanded is None
            or getattr(view, "action", None) != "_zoek"
            or selected_fields is None
        ):
            return expanded

        def select_fields(value, fields):
            if isinstance(value, list):
                return [select_fields(item, fields) for item in value]
            if not isinstance(value, dict) or fields is None:
                return value
            result = value.copy() if "*" in fields else {}
            for name, children in fields.items():
                if name in value:
                    result[name] = select_fields(value[name], children)
            inclusions = {
                name: select_fields(item, fields.get(name))
                for name, item in value.get(EXPAND_KEY, {}).items()
                if name in fields or "*" in fields
            }
            if inclusions:
                result[EXPAND_KEY] = inclusions
            return result

        if "results" in expanded:
            expanded["results"] = select_fields(expanded["results"], selected_fields)
            return expanded
        return select_fields(expanded, selected_fields)

    def _get_expanded_data(self, data, renderer_context):
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

        has_expand = getattr(view, "has_expand", None)
        expand_requested = (
            has_expand(request)
            if has_expand
            else EXPAND_QUERY_PARAM in request.query_params
            or EXPAND_QUERY_PARAM in request.data
        )
        get_inclusions = getattr(view, "get_requested_inclusions", None)
        if not expand_requested and not (get_inclusions and get_inclusions(request)):
            # Always include the empty `_expand` attribute
            if isinstance(serializer_data, list):
                for record in serializer_data:
                    record[EXPAND_KEY] = {}

            if isinstance(serializer_data, dict):
                serializer_data[EXPAND_KEY] = {}

            return render_data

        inclusion_loader = self.loader_class(get_allowed_paths(request, view=view))
        inclusions = inclusion_loader.inclusions_dict(serializer)

        if isinstance(serializer_data, list):
            for record in serializer_data:
                if record["url"] in inclusions:
                    record[EXPAND_KEY] = inclusions[record["url"]]

        if isinstance(serializer_data, dict):
            if inclusions.get(serializer_data["url"]):
                serializer_data[EXPAND_KEY] = inclusions[serializer_data["url"]]

        return render_data


def get_expand_options_for_serializer(
    serializer_class: Type[Serializer],
) -> List[tuple]:
    choices = [(opt, opt) for opt in serializer_class.inclusion_serializers]
    return choices


class SelectedFieldsExpansion:
    """Prefetch the queryset to validated selected zoek fields."""

    # Computed properties and methods can access relations that field.source does
    # not reveal. Map (model label, serializer source) to those relation paths so
    # they are prefetched only when that field is selected (including via "*").
    # Example: selecting "status" uses Zaak.current_status, which reads status_set.
    # The entry below batches that lookup instead of querying statuses per zaak.
    SOURCE_DEPENDENCIES = {
        ("zaken.relevantezaakrelatie", "url"): ("_relevant_zaak",),
        ("zaken.zaakrelatie", "url"): ("_gerelateerde_zaak",),
        ("zaken.zaak", "current_status"): ("status_set",),
        ("zaken.status", "indicatie_laatst_gezette_status"): ("zaak.status_set",),
        ("catalogi.statustype", "is_eindstatus"): ("zaaktype.statustypen",),
        ("documenten.enkelvoudiginformatieobject", "get_bestandsdelen"): (
            "canonical.bestandsdelen",
        ),
        ("documenten.enkelvoudiginformatieobject", "locked"): ("canonical",),
        ("documenten.bestandsdeel", "lock"): (
            "informatieobject.latest_version.canonical",
        ),
    }

    @staticmethod
    def fields_at_path(selected_fields, path):
        """Resolve a nested selection, None denotes an unexpanded field."""
        for name in path:
            if selected_fields is None:
                break
            selected_fields = selected_fields.get(name)
        return selected_fields

    @classmethod
    def limit_serializer_fields(cls, serializer, selected_fields):
        """Keep URL internally for expansion matching the renderer removes it later."""
        if isinstance(serializer, serializers.ListSerializer):
            serializer = serializer.child
        for name in list(serializer.fields):
            if (
                "*" not in selected_fields
                and name not in selected_fields
                and name != "url"
            ):
                del serializer.fields[name]
                continue
            field = serializer.fields[name]
            children = selected_fields.get(name)
            if children is not None and isinstance(field, serializers.BaseSerializer):
                cls.limit_serializer_fields(field, children)
        return serializer

    @classmethod
    def selected_prefetches(cls, serializer, selected_fields):
        """Follow serializer sources and explicit property dependencies recursively."""
        # Keep caches local: serializer instances must not leak between requests.
        lookups = {}
        inclusions = getattr(serializer, "inclusion_serializers", {})

        @cache
        def resolve_field(model, name):
            for candidate in ("_" + name, name):
                try:
                    return model._meta.get_field(candidate)
                except FieldDoesNotExist:
                    pass
            return next(
                (
                    field
                    for field in model._meta.get_fields()
                    if field.auto_created
                    and field.is_relation
                    and field.get_accessor_name() == name
                ),
                None,
            )

        @cache
        def inclusion_serializer(inclusion):
            serializer_class = (
                import_string(inclusion) if isinstance(inclusion, str) else inclusion
            )
            return serializer_class()

        def relation_path(model, source, prefix):
            parts = list(prefix)
            for name in source.split("."):
                field = resolve_field(model, name)
                if field is None or not field.is_relation:
                    break
                # Reverse managers use their accessor rather than query name.
                name = field.get_accessor_name() if field.auto_created else field.name
                parts.append(name)
                model = field.related_model
                lookups.setdefault("__".join(parts), None)
            return model, tuple(parts)

        def include_field(current, fields, prefix=(), api_path=()):
            model = current.Meta.model
            names = dict.fromkeys(current.fields if "*" in fields else fields)

            if "url" in current.fields:
                names["url"] = None

            for name in names:
                if name == "*":
                    continue
                field = current.fields[name]
                source = field.source
                dependencies = cls.SOURCE_DEPENDENCIES.get(
                    (model._meta.label_lower, source)
                )

                if dependencies is None:
                    dependencies = (source,) if source != "*" else ()

                for lookup in getattr(field, "parent_lookup_kwargs", {}).values():
                    relation_path(model, lookup.replace("__", "."), prefix)
                target, path = model, prefix

                for dependency in dependencies:
                    target, path = relation_path(model, dependency, prefix)

                if (
                    target._meta.label_lower
                    == "documenten.enkelvoudiginformatieobjectcanonical"
                    and hasattr(field, "get_inclusion_instance")
                ):
                    target, path = relation_path(target, "latest_version", path)

                if (
                    name in ("begin_object", "einde_object")
                    and prefix
                    and lookups["__".join(prefix)] is None
                ):
                    manager = model._default_manager
                    if hasattr(manager, "with_dates"):
                        lookups["__".join(prefix)] = manager.with_dates(
                            model.omschrijving_field
                        )

                children = fields.get(name)
                if children is None:
                    # Embedded serializers are serialized fully when selected by name.
                    if isinstance(field, serializers.BaseSerializer):
                        children = {"*": None}
                    else:
                        continue
                child_path = (*api_path, name)
                inclusion = inclusions.get(".".join(child_path))
                if inclusion:
                    include_field(
                        inclusion_serializer(inclusion), children, path, child_path
                    )
                elif isinstance(field, serializers.BaseSerializer):
                    child = (
                        field.child
                        if isinstance(field, serializers.ListSerializer)
                        else field
                    )
                    if hasattr(child, "Meta") and hasattr(child.Meta, "model"):
                        include_field(child, children, path, child_path)

        include_field(serializer, selected_fields)
        # relation_path inserts parents before children, replacing a parent's
        # queryset with date annotations preserves that order.
        return tuple(
            Prefetch(path, queryset=queryset) if queryset is not None else path
            for path, queryset in lookups.items()
        )
