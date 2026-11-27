# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_eigenschap import (
    EigenschapAPITests as _EigenschapAPITests,
    EigenschapFilterAPITests as _EigenschapFilterAPITests,
    EigenschapPaginationTestCase as _EigenschapPaginationTestCase,
)


class EigenschapAPITests(_EigenschapAPITests):
    NAMESPACE = "zaken"


class EigenschapFilterAPITests(_EigenschapFilterAPITests):
    NAMESPACE = "zaken"


class EigenschapPaginationTestCase(_EigenschapPaginationTestCase):
    NAMESPACE = "zaken"
