# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from functools import partial
from typing import Optional, Set

from django.conf import settings
from django.core.cache import cache
from django.db import models

from rest_framework_condition.decorators import condition as drf_condition
from vng_api_common.caching.etags import calculate_etag, etag_func
from vng_api_common.caching.registry import extract_dependencies

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


class CMISETagMixin:
    """
    Custom ETag management for Document API resources.

    To prevent storing ETag values for Documenten API resources in an external DMS,
    we store them in the cache.
    """

    def __hash__(self):
        if not settings.CMIS_ENABLED:
            return super().__hash__()

        # cmis model instances don't have a PK, but they should have a proper UUID
        assert self.pk is None
        return hash(self.uuid)

    @property
    def _etag(self):
        return get_etag(get_etag_cache_key(self))

    def calculate_etag_value(self) -> str:
        """
        Calculate and save the ETag value.
        """
        etag = calculate_etag(self)
        set_etag(get_etag_cache_key(self), etag)
        return etag


def cmis_conditional_retrieve(
    action="retrieve",
    etag_field="_etag",
    extra_depends_on: Optional[Set[str]] = None,
):
    """
    Decorate a viewset to apply conditional GET requests.

    The decorator patches the handler to calculate and emit the required ETag-related
    headers. Additionally, it sets up the dependency tree for the exposed resource so
    that the ETag value can be recalculated when the resource or relevant related
    resources are modified, resulting in an updated ETag value. This is introspected
    through the specified viewset serializer class.

    :param action: The viewset action to decorate
    :param etag_field: The model field containing the (cached) ETag value
    :param extra_depends_on: A set of additional field names the ETag value calculation
      depends on. Normally, this is inferred from the serializer, but in some cases (
      .e.g. ``SerializerMethodField``) this cannot be automatically detected. These
      fields will be added to the automatically introspected serializer relations.
    """

    def decorator(viewset: type):
        extract_dependencies(viewset, extra_depends_on or set())
        condition = drf_condition(etag_func=partial(etag_func, etag_field=etag_field))
        original_handler = getattr(viewset, action)

        # Explicitly add the CMIS decorator, because it is overridden otherwise
        handler = convert_cmis_adapter_exceptions(condition(original_handler))
        setattr(viewset, action, handler)
        if not hasattr(viewset, "_conditional_retrieves"):
            viewset._conditional_retrieves = []
        viewset._conditional_retrieves.append(action)
        return viewset

    return decorator
