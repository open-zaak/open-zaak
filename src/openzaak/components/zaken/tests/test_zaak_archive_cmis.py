# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/345
"""
from datetime import date

from django.test import override_settings

from rest_framework import status
from vng_api_common.constants import Archiefnominatie, Archiefstatus
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from .factories import ZaakFactory, ZaakInformatieObjectFactory
from .utils import ZAAK_WRITE_KWARGS, get_operation_url

VERANTWOORDELIJKE_ORGANISATIE = "517439943"


@require_cmis
@override_settings(CMIS_ENABLED=True)
class US345CMISTestCase(JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_root="http://testserver/documenten/api/v1/", api_type=APITypes.drc
        )
        ServiceFactory.create(
            api_root="http://testserver/catalogi/api/v1/", api_type=APITypes.ztc
        )
        ServiceFactory.create(
            api_root="http://testserver/zaken/api/v1/", api_type=APITypes.zrc
        )

    def test_can_set_archiefstatus_when_all_documents_are_gearchiveerd(self):
        zaak = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date.today(),
        )
        io = EnkelvoudigInformatieObjectFactory.create(status="gearchiveerd")
        io_url = f"http://testserver{reverse(io)}"

        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io_url)
        zaak_patch_url = get_operation_url("zaak_partial_update", uuid=zaak.uuid)
        data = {"archiefstatus": Archiefstatus.gearchiveerd}

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_cannot_set_archiefstatus_when_not_all_documents_are_gearchiveerd(self):
        zaak = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date.today(),
        )
        io = EnkelvoudigInformatieObjectFactory.create(status="in_bewerking")
        io_url = f"http://testserver{reverse(io)}"

        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io_url)
        zaak_patch_url = get_operation_url("zaak_partial_update", uuid=zaak.uuid)
        data = {"archiefstatus": Archiefstatus.gearchiveerd}

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
