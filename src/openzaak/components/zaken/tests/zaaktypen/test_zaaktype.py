# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_zaaktype import (
    ZaakTypeAPITests as _ZaakTypeAPITests,
    ZaakTypeCreateDuplicateTests as _ZaakTypeCreateDuplicateTests,
    ZaakTypeFilterAPITests as _ZaakTypeFilterAPITests,
    ZaakTypePaginationTestCase as _ZaakTypePaginationTestCase,
    ZaakTypePublishTests as _ZaakTypePublishTests,
    ZaaktypeValidationTests as _ZaaktypeValidationTests,
)


class ZaakTypeAPITests(_ZaakTypeAPITests):
    NAMESPACE = "zaken"


class ZaakTypePublishTests(_ZaakTypePublishTests):
    NAMESPACE = "zaken"


class ZaakTypeCreateDuplicateTests(_ZaakTypeCreateDuplicateTests):
    NAMESPACE = "zaken"


class ZaakTypeFilterAPITests(_ZaakTypeFilterAPITests):
    NAMESPACE = "zaken"


class ZaakTypePaginationTestCase(_ZaakTypePaginationTestCase):
    NAMESPACE = "zaken"


class ZaaktypeValidationTests(_ZaaktypeValidationTests):
    NAMESPACE = "zaken"
