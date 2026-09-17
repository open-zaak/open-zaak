# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from openzaak.components.catalogi.tests.test_caching import (
    EigenschapCacheTests as _EigenschapCacheTests,
    EigenschapCacheTransactionTests as _EigenschapCacheTransactionTests,
    M2MRelationCachingTests as _M2MRelationCachingTests,
    ResultaatTypeCacheTests as _ResultaatTypeCacheTests,
    ResultaatTypeCacheTransactionTests as _ResultaatTypeCacheTransactionTests,
    RolTypeCacheTests as _RolTypeCacheTests,
    RolTypeCacheTransactionTests as _RolTypeCacheTransactionTests,
    StatusTypeCacheTests as _StatusTypeCacheTests,
    StatusTypeCacheTransactionTests as _StatusTypeCacheTransactionTests,
    ZaakInformatieobjectTypeCacheTests as _ZaakInformatieobjectTypeCacheTests,
    ZaakInformatieobjectTypeCacheTransactionTests as _ZaakInformatieobjectTypeCacheTransactionTests,
    ZaakTypeCacheTests as _ZaakTypeCacheTests,
    ZaakTypeCacheTransactionTests as _ZaakTypeCacheTransactionTests,
)


class ZaakTypeCacheTests(_ZaakTypeCacheTests):
    NAMESPACE = "zaken"


class ZaakTypeCacheTransactionTests(_ZaakTypeCacheTransactionTests):
    NAMESPACE = "zaken"


class StatusTypeCacheTests(_StatusTypeCacheTests):
    NAMESPACE = "zaken"


class StatusTypeCacheTransactionTests(_StatusTypeCacheTransactionTests):
    NAMESPACE = "zaken"


class EigenschapCacheTests(_EigenschapCacheTests):
    NAMESPACE = "zaken"


class EigenschapCacheTransactionTests(_EigenschapCacheTransactionTests):
    NAMESPACE = "zaken"


class RolTypeCacheTests(_RolTypeCacheTests):
    NAMESPACE = "zaken"


class RolTypeCacheTransactionTests(_RolTypeCacheTransactionTests):
    NAMESPACE = "zaken"


class ResultaatTypeCacheTests(_ResultaatTypeCacheTests):
    NAMESPACE = "zaken"


class ResultaatTypeCacheTransactionTests(_ResultaatTypeCacheTransactionTests):
    NAMESPACE = "zaken"


class ZaakInformatieobjectTypeCacheTests(_ZaakInformatieobjectTypeCacheTests):
    NAMESPACE = "zaken"


class ZaakInformatieobjectTypeCacheTransactionTests(
    _ZaakInformatieobjectTypeCacheTransactionTests
):
    NAMESPACE = "zaken"


class M2MRelationCachingTests(_M2MRelationCachingTests):
    NAMESPACE = "zaken"
