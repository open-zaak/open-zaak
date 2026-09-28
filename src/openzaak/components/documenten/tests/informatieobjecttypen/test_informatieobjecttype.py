# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_informatieobjecttype import (
    InformatieObjectTypeAPITests as _InformatieObjectTypeAPITests,
    InformatieObjectTypeFilterAPITests as _InformatieObjectTypeFilterAPITests,
    InformatieObjectTypePaginationTestCase as _InformatieObjectTypePaginationTestCase,
)


class InformatieObjectTypeAPITests(_InformatieObjectTypeAPITests):
    NAMESPACE = "documenten"
    ZAAKTYPE_NAMESPACE = "zaken"


class InformatieObjectTypeFilterAPITests(_InformatieObjectTypeFilterAPITests):
    NAMESPACE = "documenten"
    ZAAKTYPE_NAMESPACE = "zaken"


class InformatieObjectTypePaginationTestCase(_InformatieObjectTypePaginationTestCase):
    NAMESPACE = "documenten"
