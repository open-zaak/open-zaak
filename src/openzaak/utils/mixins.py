# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from django.db.models import Prefetch
from django.utils.module_loading import import_string

from dictdiffer import diff
from rest_framework.exceptions import ValidationError
from rest_framework_inclusions.renderer import (
    get_allowed_paths,
)
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.models import APIMixin as _APIMixin

from .expansion import EXPAND_QUERY_PARAM, ExpandJSONRenderer
from .permissions import ExpandAuthRequired


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

    def _remove_select_related(self, qs, lookup):
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

    def get_queryset(self):
        qs = super().get_queryset()

        request = getattr(self, "request", None)

        if request is not None and hasattr(request, "data"):
            inclusions = self.get_requested_inclusions(request)
        else:
            inclusions = None

        inclusion_viewsets = getattr(self, "inclusion_viewsets", None)

        if inclusions and inclusion_viewsets:
            prefetches = list(qs._prefetch_related_lookups)

            inclusions = [inclusion.strip() for inclusion in inclusions.split(",")]

            unsupported = [
                inclusion
                for inclusion in inclusions
                if inclusion not in inclusion_viewsets
            ]

            if unsupported:
                raise ValidationError(
                    {"expand": f"Expansion '{unsupported[0]}' is not supported."}
                )
            # Sort parent lookups before nested lookups
            inclusions.sort(
                key=lambda inclusion: "__"
                in (
                    inclusion_viewsets[inclusion][0]
                    if isinstance(inclusion_viewsets[inclusion], tuple)
                    else inclusion
                )
            )

            for inclusion in inclusions:
                related_viewset = inclusion_viewsets.get(inclusion)
                if not related_viewset:
                    continue

                # The API expand name can differ from the lookup for reverse relations
                if isinstance(related_viewset, tuple):
                    lookup, viewset_path = related_viewset
                else:
                    lookup = inclusion
                    viewset_path = related_viewset

                # If the inclusion replaces a select_related lookup, remove that lookup
                qs = self._remove_select_related(qs, lookup)

                related_viewset = import_string(viewset_path)

                prefetches = [
                    prefetch
                    for prefetch in prefetches
                    if not (
                        prefetch == lookup
                        or getattr(prefetch, "prefetch_to", prefetch).startswith(
                            f"{lookup}__"
                        )
                    )
                ]

                # TODO if contains ., replace with __?
                prefetches.append(
                    Prefetch(
                        lookup,
                        queryset=related_viewset.queryset.order_by(),
                    )
                )
            # Clear the existing prefetches so the modified prefetch list can replace them
            qs = qs.prefetch_related(None).prefetch_related(*prefetches)

        return qs

    def get_renderers(self):
        # Only use the expand renderer for actions that support expansion.
        if self.action in ["list", "_zoek", "retrieve"]:
            return [ExpandJSONRenderer()]
        return super().get_renderers()

    def include_allowed(self):
        return self.action in ["list", "_zoek", "retrieve"]

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
