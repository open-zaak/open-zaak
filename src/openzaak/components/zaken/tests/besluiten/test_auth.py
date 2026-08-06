# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Guarantee that the proper authorization amchinery is in place.
"""

from openzaak.components.besluiten.tests.test_auth import (
    BesluitReadCorrectScopeTests as _BesluitReadCorrectScopeTests,
    BesluitScopeForbiddenTests as _BesluitScopeForbiddenTests,
    BesluitWriteCorrectScopeTests as _BesluitWriteCorrectScopeTests,
    BioReadTests as _BioReadTests,
    ExternalBesluittypeScopeTests as _ExternalBesluittypeScopeTests,
    InternalBesluittypeScopeTests as _InternalBesluittypeScopeTests,
)


class BesluitScopeForbiddenTests(_BesluitScopeForbiddenTests):
    NAMESPACE = "zaken"


class BesluitReadCorrectScopeTests(_BesluitReadCorrectScopeTests):
    NAMESPACE = "zaken"


class BesluitWriteCorrectScopeTests(_BesluitWriteCorrectScopeTests):
    NAMESPACE = "zaken"


class BioReadTests(_BioReadTests):
    NAMESPACE = "zaken"


class InternalBesluittypeScopeTests(_InternalBesluittypeScopeTests):
    NAMESPACE = "zaken"


class ExternalBesluittypeScopeTests(_ExternalBesluittypeScopeTests):
    NAMESPACE = "zaken"
