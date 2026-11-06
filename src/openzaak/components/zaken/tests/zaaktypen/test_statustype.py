# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_statustype import (
    StatusTypeAPITests as _StatusTypeAPITests,
    StatusTypeFilterAPITests as _StatusTypeFilterAPITests,
    StatusTypePaginationTestCase as _StatusTypePaginationTestCase,
)


class StatusTypeAPITests(_StatusTypeAPITests):
    NAMESPACE = "zaken"


class StatusTypeFilterAPITests(_StatusTypeFilterAPITests):
    NAMESPACE = "zaken"


class StatusTypePaginationTestCase(_StatusTypePaginationTestCase):
    NAMESPACE = "zaken"
