# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact

from openzaak.components.catalogi.tests.test_servicenorm import (
    ServiceNormDurationTests as _ServiceNormDurationTests,
)


class ServiceNormDurationTests(_ServiceNormDurationTests):
    NAMESPACE = "zaken"
