# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2022 Dimpact
from openzaak.components.besluiten.tests.test_audittrails import (
    AuditTrailTests as _AuditTrailTests,
    BesluitAuditTrailJWTExpiryTests as _BesluitAuditTrailJWTExpiryTests,
)


class AuditTrailTests(_AuditTrailTests):
    NAMESPACE = "zaken"


class BesluitAuditTrailJWTExpiryTests(_BesluitAuditTrailJWTExpiryTests):
    NAMESPACE = "zaken"
