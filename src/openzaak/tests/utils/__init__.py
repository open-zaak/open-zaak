# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from .admin import AdminTestMixin
from .auth import JWTAuthMixin
from .cache import ClearCachesMixin
from .factories import FkOrServiceUrlFactoryMixin
from .migrations import TestMigrations
from .mocks import (
    MockSchemasMixin,
    get_eio_response,
    mock_brc_oas_get,
    mock_cmc_oas_get,
    mock_drc_oas_get,
    mock_nrc_oas_get,
    mock_vrc_oas_get,
    mock_zrc_oas_get,
    mock_ztc_oas_get,
    patch_resource_validator,
)
from .oas import get_spec

__all__ = [
    # mocks
    "mock_brc_oas_get",
    "mock_cmc_oas_get",
    "mock_drc_oas_get",
    "mock_zrc_oas_get",
    "mock_ztc_oas_get",
    "mock_vrc_oas_get",
    "mock_nrc_oas_get",
    "MockSchemasMixin",
    "get_eio_response",
    "patch_resource_validator",
    # auth
    "JWTAuthMixin",
    # cache
    "ClearCachesMixin",
    # admin
    "AdminTestMixin",
    # oas
    "get_spec",
    # factories
    "FkOrServiceUrlFactoryMixin",
    # migrations
    "TestMigrations",
]
