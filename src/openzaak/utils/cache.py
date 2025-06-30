# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from contextlib import contextmanager
from typing import Iterable

from django.core.cache import caches

import requests_cache
from requests_cache import BaseCache, clear, install_cache, uninstall_cache
from requests_cache.policy import CacheSettings
from requests_cache.session import CachedSession


class DjangoCacheStorage(requests_cache.BaseStorage):
    """
    Custom storage for requests-cache that uses the Django cache framework
    """

    def __init__(self, cache_name: str, **kwargs):
        super().__init__(**kwargs)

        self.cache = caches[cache_name]

    def __contains__(self, key) -> bool:
        return key in self.cache

    def __getitem__(self, key):
        return self.cache.get(key)

    def __setitem__(self, key, item):
        """Save an item to the cache, optionally with TTL"""
        if getattr(item, "ttl", None):
            self.cache.set(key, item, timeout=item.ttl)
        else:
            self.cache.set(key, item)

    def __delitem__(self, key):
        self.cache.delete(key)

    def __iter__(self):
        """
        Has to be defined for the abstract base class `requests_cache.BaseStorage`, but
        is never actually used
        """
        raise NotImplementedError

    def __len__(self):
        """
        Has to be defined for the abstract base class `requests_cache.BaseStorage`, but
        is never actually used
        """
        raise NotImplementedError

    def bulk_delete(self, keys: Iterable[str]):
        """Delete multiple keys from the cache, without raising errors for missing keys"""
        self.cache.delete_many(keys)

    def clear(self):
        self.cache.clear()

    def __str__(self):
        return f"DjangoCacheStorage(cache_name={self.cache})"


class DjangoRequestsCache(requests_cache.BaseCache):
    """
    Custom cache backend for requests-cache that uses the Django cache framework
    """

    def __init__(self, cache_name: str, **kwargs):
        self.cache_name = cache_name
        self.responses = DjangoCacheStorage(cache_name=cache_name)
        self.redirects = DjangoCacheStorage(cache_name=cache_name)
        self._settings = (
            CacheSettings()
        )  # Init and public access is done in CachedSession

    def update(self, other: BaseCache):
        """Update this cache with the contents of another cache"""
        self.responses.update(other.responses)
        self.redirects.update(other.redirects)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.cache_name})>"


@contextmanager
def requests_cache_enabled(*args, **kwargs):
    """
    Custom context manager for requests-cache, to actually clear the contents of
    the cache, before uninstalling it
    """
    # Unfortunately requests-cache does not work out of the box for custom clients that
    # inherit from `requests.Session`, so we have to monkeypatch the `OpenZaakClient` to
    # ensure requests made with that client are cached as well
    import vng_api_common.client

    original_client = vng_api_common.client.Client

    cache_name = "import_requests"
    backend = DjangoRequestsCache(cache_name)

    class CustomCachedSession(CachedSession):
        def __init__(self, *args, **kwargs):
            # Initialize CachedSession with the custom backend
            # `ape_pie.APIClient` doesn't forward the cache params, causing
            # sqlite to be used by default, so we explicitly set the __init__ here
            super().__init__(
                cache_name=cache_name,
                backend=backend,
                *args,
                **kwargs,
            )

    class CustomOpenZaakClient(original_client, CustomCachedSession):
        pass

    vng_api_common.client.Client = CustomOpenZaakClient
    install_cache(cache_name=cache_name, backend=backend, *args, **kwargs)
    try:
        yield
    finally:
        vng_api_common.client.Client = original_client
        clear()
        uninstall_cache()
