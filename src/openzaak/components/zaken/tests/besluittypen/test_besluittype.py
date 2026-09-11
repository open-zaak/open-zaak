# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_besluittype import (
    BesluitTypeAPITests as _BesluitTypeAPITests,
    BesluitTypeFilterAPITests as _BesluitTypeFilterAPITests,
    BesluitTypePaginationTestCase as _BesluitTypePaginationTestCase,
    BesluitTypeValidationTests as _BesluitTypeValidationTests,
)


class BesluitTypeAPITests(_BesluitTypeAPITests):
    NAMESPACE = "zaken"
    IOT_NAMESPACE = "documenten"


class BesluitTypeFilterAPITests(_BesluitTypeFilterAPITests):
    NAMESPACE = "zaken"


class BesluitTypePaginationTestCase(_BesluitTypePaginationTestCase):
    NAMESPACE = "zaken"


class BesluitTypeValidationTests(_BesluitTypeValidationTests):
    NAMESPACE = "zaken"
