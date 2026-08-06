# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from openzaak.components.besluiten.tests.test_filters import (
    BesluitAPIFilterTests as _BesluitAPIFilterTests,
    BesluitInformatieObjectAPIFilterTests as _BesluitInformatieObjectAPIFilterTests,
    ListFilterLocalFKTests as _ListFilterLocalFKTests,
)


class ListFilterLocalFKTests(_ListFilterLocalFKTests):
    heeft_alle_autorisaties = True
    NAMESPACE = "zaken"


class BesluitAPIFilterTests(_BesluitAPIFilterTests):
    heeft_alle_autorisaties = True
    NAMESPACE = "zaken"


class BesluitInformatieObjectAPIFilterTests(_BesluitInformatieObjectAPIFilterTests):
    NAMESPACE = "zaken"
