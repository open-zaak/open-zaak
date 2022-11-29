# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Utilities to deal with OpenAPI 3 specifications.

.. warning:: this module is import at settings load-time and CANNOT use Django models
   or anything else that requires django to be configured first.
"""
from dataclasses import dataclass
from typing import Callable

__all__ = ["SPECIFICATIONS", "APIStandard"]

SPECIFICATIONS = {}


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

    @property
    def schema(self):
        """
        Download the cached schema.
        """
        raise NotImplementedError()

    def download_schema(self, fetch: Callable[[str], dict]) -> dict:
        return fetch(self.oas_url)
