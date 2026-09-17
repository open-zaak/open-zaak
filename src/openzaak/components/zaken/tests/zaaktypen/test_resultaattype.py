# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_resultaattype import (
    ResultaatTypeAPITests as _ResultaatTypeAPITests,
    ResultaatTypeFilterAPITests as _ResultaatTypeFilterAPITests,
    ResultaatTypePaginationTestCase as _ResultaatTypePaginationTestCase,
    ResultaatTypeValidationTests as _ResultaatTypeValidationTests,
)


class ResultaatTypeAPITests(_ResultaatTypeAPITests):
    NAMESPACE = "zaken"


class ResultaatTypeFilterAPITests(_ResultaatTypeFilterAPITests):
    NAMESPACE = "zaken"


class ResultaatTypePaginationTestCase(_ResultaatTypePaginationTestCase):
    NAMESPACE = "zaken"


class ResultaatTypeValidationTests(_ResultaatTypeValidationTests):
    NAMESPACE = "zaken"
