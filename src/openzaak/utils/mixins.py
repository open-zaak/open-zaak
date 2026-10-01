# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from django.utils.module_loading import import_string

from dictdiffer import diff
from rest_framework.exceptions import ValidationError
from rest_framework_inclusions.renderer import (
    get_allowed_paths,
)
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.models import APIMixin as _APIMixin

from .expansion import (
    EXPAND_QUERY_PARAM,
    ExpandJSONRenderer,
    SelectedFieldsExpansion,
)
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
    renderer_classes = (ExpandJSONRenderer,)
    expand_param = EXPAND_QUERY_PARAM

    def include_allowed(self):
        return self.action in ["list", "_zoek", "retrieve"]

    def has_expand(self, request) -> bool:
        return (
            self.expand_param in request.data
            or self.expand_param in request.query_params
        )

    def get_selected_inclusions(self, request):
        """Optional field-selected expansion paths supplied by FieldsMixin."""
        return ()

    def get_requested_inclusions(self, request):
        """Combine expansion sources for rendering and authorization."""
        if request.method == "POST" and isinstance(request.data, dict):
            requested = ",".join(
                request.data.get(self.expand_param, [])
                + [request.query_params.get(self.expand_param, "")]
            )
        else:
            requested = request.GET.get(self.expand_param)
        selected = self.get_selected_inclusions(request)
        return ",".join(filter(None, [requested, *selected])) if selected else requested

    def get_permissions(self):
        permissions = [permission() for permission in self.permission_classes]

        inclusion_serializers = getattr(
            self.get_serializer_class(), "inclusion_serializers", {}
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
    """Validate search fields and expose their serialization dependencies."""

    _selected_fields: dict | None = None
    _selected_inclusions: tuple[str, ...] | None = None

    def has_fields(self, request) -> bool:
        """Check whether the zoek request includes a fields selection"""
        return self.action == "_zoek" and "fields" in request.data

    def get_search_input(self):
        """Validate search filters while reusing the already validated fields."""
        serializer = self.get_search_input_serializer_class()(
            data=self.request.data, context=self.get_serializer_context()
        )
        if self._selected_fields is not None:
            del serializer.fields["fields"]
        serializer.is_valid(raise_exception=True)
        search_input = serializer.validated_data.copy()
        self._selected_fields = search_input.pop("fields", self._selected_fields)
        return search_input

    def get_selected_inclusions(self, request):
        """Expose selected paths, ExpandMixin handles their authorization."""
        if not self.has_fields(request):
            return ()

        if self._selected_fields is None:
            field = self.get_search_input_serializer_class()().fields["fields"]
            try:
                self._selected_fields = field.run_validation(request.data["fields"])
            except ValidationError as exc:
                raise ValidationError({"fields": exc.detail}) from exc
        if self._selected_inclusions is None:
            self._selected_inclusions = tuple(
                path
                for path in self.get_serializer_class().inclusion_serializers
                if SelectedFieldsExpansion.fields_at_path(
                    self._selected_fields, path.split(".")
                )
                is not None
            )
        return self._selected_inclusions

    def add_zoek_fields_prefetch(self, queryset):
        """Load dependencies for selected fields or full requested expansions."""
        selected_fields = self._selected_fields
        if selected_fields is None and self.has_expand(self.request):
            # Legacy expand returns all fields at each requested level. Build a
            # planning selection without changing response field selection.
            selected_fields = {"*": None}
            paths = get_allowed_paths(self.request, view=self)
            if paths is None:
                paths = (
                    path.split(".")
                    for path in self.get_serializer_class().inclusion_serializers
                )
            for path in paths:
                children = selected_fields
                for name in path:
                    children = children.setdefault(name, {"*": None})
        if selected_fields is not None:
            return queryset.prefetch_related(None).prefetch_related(
                *SelectedFieldsExpansion.selected_prefetches(
                    self.get_serializer_class()(), selected_fields
                )
            )
        return queryset

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        if self._selected_fields is not None:
            SelectedFieldsExpansion.limit_serializer_fields(
                serializer, self._selected_fields
            )
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
