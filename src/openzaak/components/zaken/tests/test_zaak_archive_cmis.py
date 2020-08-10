# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/345
"""
from datetime import date

from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.constants import Archiefnominatie, Archiefstatus
from vng_api_common.tests import reverse

from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin, serialise_eio

from .factories import ZaakInformatieObjectFactory
from .utils import ZAAK_WRITE_KWARGS, get_operation_url

VERANTWOORDELIJKE_ORGANISATIE = "517439943"


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class US345CMISTestCase(JWTAuthMixin, APICMISTestCase, OioMixin):

    heeft_alle_autorisaties = True

    def test_can_set_archiefstatus_when_all_documents_are_gearchiveerd(self):
        self.create_zaak_besluit_services()
        zaak = self.create_zaak(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date.today(),
        )
        io = EnkelvoudigInformatieObjectFactory.create(status="gearchiveerd")
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io_url)
        zaak_patch_url = get_operation_url("zaak_partial_update", uuid=zaak.uuid)
        data = {"archiefstatus": Archiefstatus.gearchiveerd}

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_cannot_set_archiefstatus_when_not_all_documents_are_gearchiveerd(self):
        self.create_zaak_besluit_services()
        zaak = self.create_zaak(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date.today(),
        )
        io = EnkelvoudigInformatieObjectFactory.create(status="in_bewerking")
        io_url = f"http://testserver{reverse(io)}"
        self.adapter.get(io_url, json=serialise_eio(io, io_url))
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io_url)
        zaak_patch_url = get_operation_url("zaak_partial_update", uuid=zaak.uuid)
        data = {"archiefstatus": Archiefstatus.gearchiveerd}

        response = self.client.patch(zaak_patch_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
