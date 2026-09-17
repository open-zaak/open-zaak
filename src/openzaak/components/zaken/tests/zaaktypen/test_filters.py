# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_filters import (
    EigenschapFilterTests as _EigenschapFilterTests,
    ResultaatTypeFilterTests as _ResultaatTypeFilterTests,
    RolTypeFilterTests as _RolTypeFilterTests,
    StatusTypeFilterTests as _StatusTypeFilterTests,
    ZaakTypeFilterTests as _ZaakTypeFilterTests,
    ZaakTypeInformatieObjectTypeFilterTests as _ZaakTypeInformatieObjectTypeFilterTests,
)


class ZaakTypeFilterTests(_ZaakTypeFilterTests):
    NAMESPACE = "zaken"


class StatusTypeFilterTests(_StatusTypeFilterTests):
    NAMESPACE = "zaken"


class EigenschapFilterTests(_EigenschapFilterTests):
    NAMESPACE = "zaken"


class RolTypeFilterTests(_RolTypeFilterTests):
    NAMESPACE = "zaken"


class ResultaatTypeFilterTests(_ResultaatTypeFilterTests):
    NAMESPACE = "zaken"


class ZaakTypeInformatieObjectTypeFilterTests(_ZaakTypeInformatieObjectTypeFilterTests):
    NAMESPACE = "zaken"
