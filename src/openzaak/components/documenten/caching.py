# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from functools import partial
from typing import Optional, Set

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.http import Http404, HttpRequest

from rest_framework_condition.decorators import condition as drf_condition
from vng_api_common.caching.etags import calculate_etag, etag_func
from vng_api_common.caching.models import ETagMixin
from vng_api_common.caching.registry import extract_dependencies
from vng_api_common.utils import get_resource_for_path

from openzaak.utils.decorators import convert_cmis_adapter_exceptions


def get_etag_cache_key(obj: models.Model) -> str:
    resource = obj._meta.model_name
    uuid = obj.uuid
    versie = getattr(obj, "versie", 1)
    return f"{resource}-{uuid}-{versie}"


def set_etag(key: str, etag_value: str) -> None:
    cache.set(key, etag_value)


def get_etag(key: str) -> Optional[str]:
    return cache.get(key)


class CMISETagMixin(ETagMixin):
    def calculate_etag_value(self) -> str:
        """
        Calculate and save the ETag value.
        """
        if settings.CMIS_ENABLED:
            etag = calculate_etag(self)
            set_etag(get_etag_cache_key(self), etag)
            return etag
        return super().calculate_etag_value()

    class Meta:
        abstract = True


@convert_cmis_adapter_exceptions
def cmis_etag_func(request: HttpRequest, etag_field: str = "_etag", **view_kwargs):
    if not settings.CMIS_ENABLED:
        return etag_func(request, etag_field=etag_field, **view_kwargs)

    try:
        obj = get_resource_for_path(request.path)
    except ObjectDoesNotExist:
        raise Http404
    # Retrieve ETag from the cache
    etag_value = get_etag(get_etag_cache_key(obj))
    if not etag_value:  # calculate missing value and store it
        etag_value = obj.calculate_etag_value()
    return etag_value


def cmis_conditional_retrieve(
    action="retrieve", etag_field="_etag", extra_depends_on: Optional[Set[str]] = None,
):
    """
    Decorate a viewset to apply conditional GET requests.

    Modified to use a cache to store/retrieve ETags in case of CMIS
    """

    def decorator(viewset: type):
        extract_dependencies(viewset, extra_depends_on or set())
        condition = drf_condition(
            etag_func=partial(cmis_etag_func, etag_field=etag_field)
        )
        original_handler = getattr(viewset, action)
        handler = condition(original_handler)
        setattr(viewset, action, handler)
        if not hasattr(viewset, "_conditional_retrieves"):
            viewset._conditional_retrieves = []
        viewset._conditional_retrieves.append(action)
        return viewset

    return decorator
