# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.db import models

from vng_api_common.caching.etags import calculate_etag


def get_etag_cache_key(obj: models.Model) -> str:
    resource = obj._meta.model_name
    uuid = obj.uuid
    versie = getattr(obj, "versie", 1)
    return f"{resource}-{uuid}-{versie}"


def set_etag(key: str, etag_value: str) -> None:
    cache.set(key, etag_value)


def get_etag(key: str) -> Optional[str]:
    return cache.get(key)


# deprecated but needed for migrations
class CMISETagMixin:
    """
    Custom ETag management for Document API resources.

    To prevent storing ETag values for Documenten API resources in an external DMS,
    we store them in the cache.
    """

    def __hash__(self):
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
