# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from .admin import AdminTestMixin
from .auth import JWTAuthMixin, generate_jwt_auth
from .cache import ClearCachesMixin
from .cmis import (
    APICMISTestCase,
    APICMISTransactionTestCase,
    require_cmis,
    serialise_eio,
)
from .mocks import (
    MockSchemasMixin,
    get_eio_response,
    mock_brc_oas_get,
    mock_drc_oas_get,
    mock_nrc_oas_get,
    mock_zrc_oas_get,
    mock_ztc_oas_get,
)

__all__ = [
    # mocks
    "mock_brc_oas_get",
    "mock_drc_oas_get",
    "mock_zrc_oas_get",
    "mock_ztc_oas_get",
    "mock_nrc_oas_get",
    "MockSchemasMixin",
    "get_eio_response",
    # auth
    "JWTAuthMixin",
    "generate_jwt_auth",
    # cache
    "ClearCachesMixin",
    # admin
    "AdminTestMixin",
    # cmis
    "APICMISTestCase",
    "APICMISTransactionTestCase",
    "serialise_eio",
    "require_cmis",
]
