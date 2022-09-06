# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag

from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import APICMISTestCase, require_cmis

from ...models import ObjectInformatieObject
from ..factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenCMISFactory


@require_cmis
@override_settings(CMIS_ENABLED=True, ALLOWED_HOSTS=["testserver", "example.com"])
class UniqueRepresentationTestCase(APICMISTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            api_root="http://testserver/catalogi/api/v1/", api_type=APITypes.ztc
        )
        Service.objects.create(
            api_root="http://testserver/zaken/api/v1/", api_type=APITypes.zrc
        )

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
    def test_oio_with_verzoek(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            bronorganisatie="730924658",
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )
        eio_url = f"http://testserver{reverse(eio)}"

        oio = ObjectInformatieObject.objects.create(
            informatieobject=eio_url,
            verzoek="http://example.com/api/v1/verzoeken/123",
            object_type="verzoek",
        )

        # not a model we can generate a representation for -> take the last fragment
        # of the API URL
        self.assertEqual(
            oio.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 123",
        )
