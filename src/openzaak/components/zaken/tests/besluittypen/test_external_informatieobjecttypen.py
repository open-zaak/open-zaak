# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact

from openzaak.components.catalogi.tests.test_external_informatieobjecttypen import (
    BesluitTypeExternalInformatieObjectTypenConceptTests as _BesluitTypeExternalInformatieObjectTypenConceptTests,
    BesluitTypeExternalInformatieObjectTypenTests as _BesluitTypeExternalInformatieObjectTypenTests,
)


class BesluitTypeExternalInformatieObjectTypenTests(
    _BesluitTypeExternalInformatieObjectTypenTests
):
    NAMESPACE = "zaken"
    INFORMATIEOBJECTTYPE_NAMESPACE = "documenten"


class BesluitTypeExternalInformatieObjectTypenConceptTests(
    _BesluitTypeExternalInformatieObjectTypenConceptTests
):
    NAMESPACE = "zaken"
