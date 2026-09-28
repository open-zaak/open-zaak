# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_roltype import (
    FilterValidationTests as _FilterValidationTests,
    RolTypeAPITests as _RolTypeAPITests,
    RolTypeFilterAPITests as _RolTypeFilterAPITests,
    RolTypePaginationTestCase as _RolTypePaginationTestCase,
)


class RolTypeAPITests(_RolTypeAPITests):
    NAMESPACE = "zaken"


class FilterValidationTests(_FilterValidationTests):
    NAMESPACE = "zaken"


class RolTypeFilterAPITests(_RolTypeFilterAPITests):
    NAMESPACE = "zaken"


class RolTypePaginationTestCase(_RolTypePaginationTestCase):
    NAMESPACE = "zaken"
