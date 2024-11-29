# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag

import requests_mock
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.contrib.verzoeken.tests.utils import get_verzoek_response
from openzaak.tests.utils import APICMISTestCase, mock_vrc_oas_get, require_cmis

from ...models import ObjectInformatieObject
from ..factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenCMISFactory


@require_cmis
@override_settings(CMIS_ENABLED=True, ALLOWED_HOSTS=["testserver", "example.com"])
class UniqueRepresentationTestCase(APICMISTestCase):
    def test_eio(self):
        eio = EnkelvoudigInformatieObjectFactory(
            bronorganisatie="730924658",
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )

        self.assertEqual(
            eio.unique_representation(),
            "730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04",
        )

    def test_gebruiksrechten(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            bronorganisatie="730924658",
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )
        eio_url = f"http://testserver{reverse(eio)}"
        gebruiksrechten = GebruiksrechtenCMISFactory(
            informatieobject=eio_url, omschrijving_voorwaarden="some conditions"
        )

        self.assertEqual(
            gebruiksrechten.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - some conditions",
        )

    @tag("oio")
    def test_oio(self):
        zaak = ZaakFactory.create(**{"identificatie": 12345})
        eio = EnkelvoudigInformatieObjectFactory.create(
            bronorganisatie="730924658",
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )
        eio_url = f"http://testserver{reverse(eio)}"

        oio = ObjectInformatieObject.objects.create(
            informatieobject=eio_url, zaak=zaak, object_type="zaak"
        )

        self.assertEqual(
            oio.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 12345",
        )

    @tag("oio", "external-urls")
    @requests_mock.Mocker(real_http=True)
    def test_oio_with_verzoek(self, m):
        vrs_base = "http://example.com/api/v1/"
        verzoek = f"{vrs_base}verzoeken/123"

        # set up mocks
        mock_vrc_oas_get(m, oas_url=f"{vrs_base}schema/openapi.yaml?v=3")
        m.get(verzoek, json=get_verzoek_response(verzoek))

        # set up model objects
        ServiceFactory.create(api_root=vrs_base, api_type=APITypes.vrc)
        eio = EnkelvoudigInformatieObjectFactory.create(
            bronorganisatie="730924658",
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )
        eio_url = f"http://testserver{reverse(eio)}"

        oio = ObjectInformatieObject.objects.create(
            informatieobject=eio_url,
            verzoek=verzoek,
            object_type="verzoek",
        )

        # not a model we can generate a representation for -> take the last fragment
        # of the API URL
        self.assertEqual(
            oio.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 123",
        )
