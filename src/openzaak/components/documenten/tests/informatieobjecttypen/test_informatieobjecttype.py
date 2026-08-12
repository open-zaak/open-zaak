# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_informatieobjecttype import (
    InformatieObjectTypeAPITests as _InformatieObjectTypeAPITests,
    InformatieObjectTypeFilterAPITests as _InformatieObjectTypeFilterAPITests,
    InformatieObjectTypePaginationTestCase as _InformatieObjectTypePaginationTestCase,
)


class InformatieObjectTypeAPITests(_InformatieObjectTypeAPITests):
    NAMESPACE = "documenten"


class InformatieObjectTypeFilterAPITests(_InformatieObjectTypeFilterAPITests):
    NAMESPACE = "documenten"


class InformatieObjectTypePaginationTestCase(_InformatieObjectTypePaginationTestCase):
    NAMESPACE = "documenten"
