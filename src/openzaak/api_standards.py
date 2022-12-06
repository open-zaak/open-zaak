# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Utilities to deal with OpenAPI 3 specifications.

.. warning:: this module is import at settings load-time and CANNOT use Django models
   or anything else that requires django to be configured first.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import requests
import yaml

__all__ = ["SPECIFICATIONS", "APIStandard"]

SPECIFICATIONS: Dict[str, "APIStandard"] = {}


@dataclass
class APIStandard:
    alias: str  # unique alias
    oas_url: str  # URL to download the API spec from if it doesn't exist in cache
    is_standardized: bool = True
    """
    Track whether an API "standard" is actually an official VNG standard.
    """

    def __post_init__(self):
        self._register()

    def _register(self) -> None:
        """
        Register itself with the global specifications registry.
        """
        if self.alias in SPECIFICATIONS:
            raise ValueError(f"Non-unique alias '{self.alias}' given.")
        SPECIFICATIONS[self.alias] = self

    def _get_cache_path(self) -> Path:
        from django.conf import settings

        cache_dir = Path(settings.BASE_DIR) / "cache"
        return cache_dir / f"{self.alias}.yaml"

    def write_cache(self) -> None:
        """
        Retrieve the API specs and write to the cache path.
        """
        response = requests.get(self.oas_url)
        response.raise_for_status()
        cache_path = self._get_cache_path()
        cache_path.write_bytes(response.content)

    @property
    def schema(self) -> dict:
        """
        Download the (cached) schema.
        """
        from vng_api_common.oas import fetcher

        # check the existing fetcher cache, as it's (usually) in-memory and therefore
        # the fastest since we avoid disk IO
        if self.oas_url in fetcher.cache:
            return fetcher.cache[self.oas_url]

        # check the on-disk cache before hitting the network
        cache_path = self._get_cache_path()
        if cache_path.exists() and cache_path.is_file():
            with cache_path.open("rb") as infile:
                spec = yaml.safe_load(infile)

            # cache the result
            fetcher.cache[self.oas_url] = spec

        # fallback to downloading from the web
        return fetcher.fetch(self.oas_url)
