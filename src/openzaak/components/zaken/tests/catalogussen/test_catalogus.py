# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_catalogus import (
    CatalogusAPITests as _CatalogusAPITests,
    CatalogusFilterAPITests as _CatalogusFilterAPITests,
    CatalogusPaginationTestCase as _CatalogusPaginationTestCase,
)


class CatalogusAPITests(_CatalogusAPITests):
    NAMESPACE = "zaken"


class CatalogusFilterAPITests(_CatalogusFilterAPITests):
    NAMESPACE = "zaken"


class CatalogusPaginationTestCase(_CatalogusPaginationTestCase):
    NAMESPACE = "zaken"
