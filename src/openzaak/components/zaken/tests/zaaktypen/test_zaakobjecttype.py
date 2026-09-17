# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from openzaak.components.catalogi.tests.test_zaakobjecttype import (
    ZaakObjectTypeAPITests as _ZaakObjectTypeAPITests,
    ZaakObjectTypeFilterAPITests as _ZaakObjectTypeFilterAPITests,
    ZaakObjectTypePaginationTests as _ZaakObjectTypePaginationTests,
)


class ZaakObjectTypeAPITests(_ZaakObjectTypeAPITests):
    NAMESPACE = "zaken"


class ZaakObjectTypeFilterAPITests(_ZaakObjectTypeFilterAPITests):
    NAMESPACE = "zaken"


class ZaakObjectTypePaginationTests(_ZaakObjectTypePaginationTests):
    NAMESPACE = "zaken"
