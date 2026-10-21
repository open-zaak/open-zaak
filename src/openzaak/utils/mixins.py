# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from django.db.models import Prefetch, QuerySet
from django.utils.module_loading import import_string

from dictdiffer import diff
from rest_framework_inclusions.renderer import (
    get_allowed_paths,
)
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.models import APIMixin as _APIMixin

from .expansion import (
    EXPAND_QUERY_PARAM,
    ExpandJSONRenderer,
    fields_at_path,
    limit_serializer_fields,
)
from .permissions import ExpandAuthRequired

EXPAND_SUPPORTED_ACTIONS = ["list", "_zoek", "retrieve"]


def format_dict_diff(changes):
    res = []
    for change in changes:
        if change[0] == "add" or change[0] == "remove":
            if not change[1]:
                res.append((change[0], dict(change[2])))
        elif change[0] == "change":
            res.append((change[0], {change[1]: change[2]}))
    return res


class AuditTrailMixin:
    @property
    def audittrail(self):
        qs = AuditTrail.objects.filter(
            hoofd_object__contains=self.get_absolute_api_url(version=1)
        ).order_by("-aanmaakdatum")
        res = []
        for audit in qs:
            oud = audit.oud or {}
            nieuw = audit.nieuw or {}

            changes = format_dict_diff(list(diff(oud, nieuw)))
            res.append((audit, changes))
        return res


class APIMixin(_APIMixin):
    def get_absolute_api_url(self, request=None, **kwargs) -> str:
        kwargs["version"] = "1"
        return super().get_absolute_api_url(request=request, **kwargs)


class ExpandMixin:
    expand_param = EXPAND_QUERY_PARAM
    inclusion_viewsets = None

    def _remove_select_related(self, qs, lookup):
        """
        Remove a select_related lookup so the expanded relation can be loaded
        with prefetch_related using the related viewset's queryset.
        Without this, expanding ``zaaktype`` on EigenschapViewSet can result
        in ~1200 queries instead of ~15.
        """
        select_related = qs.query.select_related

        if not select_related or select_related is True:
            return qs

        parts = lookup.split("__")
        current = select_related

        for part in parts[:-1]:
            current = current.get(part)
            if current is None:
                return qs

        current.pop(parts[-1], None)
        return qs

    def _prefetch_inclusion(
        self, queryset: QuerySet, lookup: str, related_queryset: QuerySet
    ) -> QuerySet:
        """Update the queryset to fetch the requested related objects in advance"""

        current_prefetches = queryset._prefetch_related_lookups
        parent_lookup, separator, child_lookup = lookup.partition("__")

        # Prefetch nested relations recursively to avoid queries per object
        if separator:
            for index, prefetch in enumerate(current_prefetches):
                if (
                    isinstance(prefetch, Prefetch)
                    and prefetch.queryset is not None
                    and parent_lookup
                    in (prefetch.prefetch_through, prefetch.prefetch_to)
                ):
                    prefetches = list(current_prefetches)
                    prefetches[index] = Prefetch(
                        prefetch.prefetch_through,
                        queryset=self._prefetch_inclusion(
                            prefetch.queryset, child_lookup, related_queryset
                        ),
                        to_attr=prefetch.to_attr,
                    )
                    return queryset.prefetch_related(None).prefetch_related(*prefetches)

        # Replace this relation's prefetch, keeping all unrelated prefetches
        prefetches = []
        existing = None
        child_prefix = f"{lookup}__"
        for prefetch in current_prefetches:
            source = getattr(prefetch, "prefetch_through", prefetch)
            destination = getattr(prefetch, "prefetch_to", prefetch)
            if isinstance(prefetch, Prefetch) and lookup in (source, destination):
                existing = prefetch
                continue

            if source != lookup and not destination.startswith(child_prefix):
                prefetches.append(prefetch)

        # Preserve aliases and ordering from the existing prefetch
        to_attr = None
        if existing is not None:
            lookup = existing.prefetch_through
            to_attr = existing.to_attr
            if existing.queryset is not None:
                related_queryset = related_queryset.order_by(
                    *existing.queryset.query.order_by
                )

        queryset = self._remove_select_related(queryset, lookup)
        prefetches.append(Prefetch(lookup, queryset=related_queryset, to_attr=to_attr))
        return queryset.prefetch_related(None).prefetch_related(*prefetches)

    def get_queryset(self):
        qs = super().get_queryset()

        request = getattr(self, "request", None)

        if request is not None and hasattr(request, "data"):
            inclusions = self.get_requested_inclusions(request)
        else:
            inclusions = None

        inclusion_viewsets = self.inclusion_viewsets

        if inclusions and inclusion_viewsets:
            inclusions = list(set(map(str.strip, inclusions.split(","))) - {""})

            # Sort parent lookups before nested lookups.
            inclusions.sort(key=lambda inclusion: (inclusion.count("."), inclusion))

            for inclusion in inclusions:
                related_viewset = inclusion_viewsets.get(inclusion)
                if not related_viewset:
                    continue

                # The API expand name can differ from the lookup for reverse relations.
                if isinstance(related_viewset, tuple):
                    lookup, viewset_path = related_viewset
                else:
                    lookup = inclusion
                    viewset_path = related_viewset

                related_viewset = import_string(viewset_path)
                qs = self._prefetch_inclusion(
                    qs, lookup, related_viewset.queryset.all()
                )

        return qs

    def get_renderers(self):
        # Only use the expand renderer for actions that support expansion.
        if self.action in EXPAND_SUPPORTED_ACTIONS:
            return [ExpandJSONRenderer()]
        return super().get_renderers()

    def include_allowed(self):
        return self.action in EXPAND_SUPPORTED_ACTIONS

    def has_expand(self, request) -> bool:
        return (
            self.expand_param in request.data
            or self.expand_param in request.query_params
        )

    def get_requested_inclusions(self, request):
        # Pull expand parameter from request body and/or query_param in case of _zoek operation
        if request.method == "POST":
            if isinstance(request.data, dict):
                return ",".join(
                    request.data.get(self.expand_param, [])
                    + [request.query_params.get(self.expand_param, "")]
                )
        return request.GET.get(self.expand_param)

    def get_permissions(self):
        permissions = [permission() for permission in self.permission_classes]

        inclusion_serializers = getattr(
            self.get_serializer(), "inclusion_serializers", {}
        )
        inclusions = get_allowed_paths(self.request, view=self)

        expand_serializers = set()

        for inclusion in inclusions:
            inclusion_path = ".".join(inclusion)
            serializer = inclusion_serializers.get(inclusion_path)
            if serializer is not None:
                expand_serializers.add(import_string(serializer))

        if expand_serializers:
            permissions.append(ExpandAuthRequired(expand_serializers))

        return permissions


class FieldsMixin:
    """
    Validate and cache search filters and field selections.
    Limit serializer fields and provide selected expansion paths.
    Place before ExpandMixin and SearchMixin in the viewset's bases.
    """

    _search_input: dict | None = None
    _selected_fields: dict | None = None
    _selected_inclusions: tuple[str, ...] | None = None

    def has_fields(self, request) -> bool:
        """Check whether the zoek request includes a fields selection"""
        return getattr(self, "action", None) == "_zoek" and "fields" in request.data

    def get_search_input(self):
        """Validate the request once, store the selected fields, and return search filters"""
        if self._search_input is None:
            serializer = self.get_search_input_serializer_class()(
                data=self.request.data, context=self.get_serializer_context()
            )
            serializer.is_valid(raise_exception=True)
            self._search_input = serializer.validated_data.copy()
            self._selected_fields = self._search_input.pop("fields", None)
        return self._search_input

    def get_requested_inclusions(self, request):
        """Return expansion paths for nested field selections"""

        if not self.has_fields(request):
            return super().get_requested_inclusions(request)

        if self._selected_fields is None:
            self.get_search_input()

        if self._selected_inclusions is None:
            self._selected_inclusions = tuple(
                path
                for path in self.get_serializer_class().inclusion_serializers
                if fields_at_path(self._selected_fields, path.split(".")) is not None
            )

        return ",".join(self._selected_inclusions)

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)

        if self._selected_fields is not None:
            limit_serializer_fields(serializer, self._selected_fields)
        return serializer


class CacheQuerysetMixin:
    """
    Mixin for ViewSets to avoid doing redundant calls to `ViewSet.get_queryset()`

    NOTE: make sure that this mixin is applied before any other mixins that override
    `get_queryset`

    `get_queryset` is actually an additional time when pagination is applied to
    an endpoint, similarly it is called an additional time when query parameters are used
    to filter the queryset. To avoid constructing the exact same queryset twice, we cache
    the result on the ViewSet instance which is a different instance for every request,
    so this caching will only be applied for the same request
    """

    _cached_queryset = None

    def get_queryset(self):
        # `get_queryset` is actually executed twice when pagination is applied to
        # an endpoint, to avoid constructing the exact same queryset twice, we cache
        # the result on the ViewSet instance which is a different instance for every request,
        # so this caching will only be applied for the same request
        if self._cached_queryset is None:
            self._cached_queryset = super().get_queryset()
        return self._cached_queryset
