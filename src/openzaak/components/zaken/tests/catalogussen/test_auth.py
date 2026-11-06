# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.catalogi.tests.test_auth import ReadTests as _ReadTests


class ReadTests(_ReadTests):
    NAMESPACE = "zaken"
