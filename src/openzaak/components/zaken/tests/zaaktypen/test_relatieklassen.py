# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_relatieklassen import (
    ZaakTypeInformatieObjectTypeAPITests as _ZaakTypeInformatieObjectTypeAPITests,
    ZaakTypeInformatieObjectTypeFilterAPITests as _ZaakTypeInformatieObjectTypeFilterAPITests,
    ZaakTypeInformatieObjectTypePaginationTestCase as _ZaakTypeInformatieObjectTypePaginationTestCase,
    ZaakTypeInformatieObjectTypeValidationTests as _ZaakTypeInformatieObjectTypeValidationTests,
)


class ZaakTypeInformatieObjectTypeAPITests(_ZaakTypeInformatieObjectTypeAPITests):
    NAMESPACE = "zaken"
    IOT_NAMESPACE = "documenten"


class ZaakTypeInformatieObjectTypeFilterAPITests(
    _ZaakTypeInformatieObjectTypeFilterAPITests
):
    NAMESPACE = "zaken"
    IOT_NAMESPACE = "documenten"


class ZaakTypeInformatieObjectTypePaginationTestCase(
    _ZaakTypeInformatieObjectTypePaginationTestCase
):
    NAMESPACE = "zaken"


class ZaakTypeInformatieObjectTypeValidationTests(
    _ZaakTypeInformatieObjectTypeValidationTests
):
    NAMESPACE = "zaken"
    IOT_NAMESPACE = "documenten"
