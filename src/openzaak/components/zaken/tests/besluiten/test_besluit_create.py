# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact


from openzaak.components.besluiten.tests.test_besluit_create import (
    BesluitCreateTests as _BesluitCreateTests,
)


class BesluitCreateTests(_BesluitCreateTests):
    NAMESPACE = "zaken"
