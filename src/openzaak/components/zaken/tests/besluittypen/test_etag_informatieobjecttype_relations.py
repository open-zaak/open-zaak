# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact

from openzaak.components.catalogi.tests.test_etag_informatieobjecttype_relations import (
    InformatieObjectTypeRelationETagTests as _InformatieObjectTypeRelationETagTests,
)


class InformatieObjectTypeRelationETagTests(_InformatieObjectTypeRelationETagTests):
    NAMESPACE = "zaken"
