# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings

from dictdiffer import diff
from drc_cmis import client_builder
from drc_cmis.connections import use_cmis_connection_pool
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.models import APIMixin as _APIMixin

from openzaak.utils.decorators import convert_cmis_adapter_exceptions

from .exceptions import CMISNotSupportedException
from .expansion import EXPAND_QUERY_PARAM, ExpandJSONRenderer


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


class CMISClientMixin:
    _cmis_client = None

    @property
    def cmis_client(self):
        if self._cmis_client is None:
            self._cmis_client = client_builder.get_cmis_client()
        return self._cmis_client


class ConvertCMISAdapterExceptions:
    @convert_cmis_adapter_exceptions
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @convert_cmis_adapter_exceptions
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @convert_cmis_adapter_exceptions
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @convert_cmis_adapter_exceptions
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @convert_cmis_adapter_exceptions
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @convert_cmis_adapter_exceptions
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class CMISConnectionPoolMixin:
    def dispatch(self, request, *args, **kwargs):
        with use_cmis_connection_pool():
            return super().dispatch(request, *args, **kwargs)


class APIMixin(_APIMixin):
    def get_absolute_api_url(self, request=None, **kwargs) -> str:
        kwargs["version"] = "1"
        return super().get_absolute_api_url(request=request, **kwargs)


class ExpandMixin:
    renderer_classes = (ExpandJSONRenderer,)
    expand_param = EXPAND_QUERY_PARAM

    def include_allowed(self):
        return self.action in ["list", "_zoek", "retrieve"]

    def get_requested_inclusions(self, request):
        # Pull expand parameter from request body in case of _zoek operation
        if request.method == "POST":
            return ",".join(request.data.get(self.expand_param, []))
        return request.GET.get(self.expand_param)

    def list(self, request, *args, **kwargs):
        expand_param = self.get_requested_inclusions(request)
        if settings.CMIS_ENABLED and expand_param:
            raise CMISNotSupportedException()

        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        expand_param = self.get_requested_inclusions(request)
        if settings.CMIS_ENABLED and expand_param:
            raise CMISNotSupportedException()

        return super().retrieve(request, *args, **kwargs)


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
