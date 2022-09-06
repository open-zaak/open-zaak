# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from datetime import date

from django.test import override_settings

from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.tests.utils import APICMISTestCase, require_cmis

from ..factories import EnkelvoudigInformatieObjectFactory


@require_cmis
@override_settings(CMIS_ENABLED=True)
class CMISEIOTests(APICMISTestCase):
    def test_default_identificatie_is_equal_to_uuid(self):
        Service.objects.create(
            api_root="http://testserver/catalogi/api/v1/", api_type=APITypes.ztc
        )
        eio = EnkelvoudigInformatieObjectFactory.create(
            identificatie="", creatiedatum=date(2019, 7, 1)
        )

        self.assertEqual(eio.identificatie, str(eio.uuid))
