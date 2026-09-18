# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact


from openzaak.components.catalogi.tests.test_filters import (
    InformatieObjectTypeFilterTests as _InformatieObjectTypeFilterTests,
)


class InformatieObjectTypeFilterTests(_InformatieObjectTypeFilterTests):
    NAMESPACE = "documenten"
