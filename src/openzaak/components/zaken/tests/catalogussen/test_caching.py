# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from openzaak.components.catalogi.tests.test_caching import (
    CatalogusCacheTests as _CatalogusCacheTests,
    CatalogusCacheTransactionTests as _CatalogusCacheTransactionTests,
)


class CatalogusCacheTests(_CatalogusCacheTests):
    NAMESPACE = "zaken"


class CatalogusCacheTransactionTests(_CatalogusCacheTransactionTests):
    NAMESPACE = "zaken"
