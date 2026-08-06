# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.besluiten.tests.test_validation import (
    BesluitInformatieObjectTests as _BesluitInformatieObjectTests,
    BesluitValidationTests as _BesluitValidationTests,
)


class BesluitValidationTests(_BesluitValidationTests):
    NAMESPACE = "zaken"


class BesluitInformatieObjectTests(_BesluitInformatieObjectTests):
    NAMESPACE = "zaken"
