# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact

from openzaak.components.catalogi.tests.test_external_informatieobjecttypen import (
    ZaakTypeInformatieObjectTypeExternalTests as _ZaakTypeInformatieObjectTypeExternalTests,
)


class ZaakTypeInformatieObjectTypeExternalTests(
    _ZaakTypeInformatieObjectTypeExternalTests
):
    NAMESPACE = "zaken"
