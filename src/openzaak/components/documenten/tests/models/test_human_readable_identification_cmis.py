# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from django.test import override_settings, tag

from openzaak.tests.utils import APICMISTestCase

from ..factories import EnkelvoudigInformatieObjectFactory


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class CMISEIOTests(APICMISTestCase):
    def test_default_identificatie_is_equal_to_uuid(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            identificatie="", creatiedatum=date(2019, 7, 1)
        )

        self.assertEqual(eio.identificatie, str(eio.uuid))
