# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.test import override_settings, tag

from vng_api_common.tests import reverse

from openzaak.utils.tests import APICMISTestCase, OioMixin

from ...models import ObjectInformatieObject
from ..factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenCMISFactory


@tag("cmis")
@override_settings(CMIS_ENABLED=True, ALLOWED_HOSTS=["testserver", "example.com"])
class UniqueRepresentationTestCase(APICMISTestCase, OioMixin):
    def test_eio(self):
        eio = EnkelvoudigInformatieObjectFactory(
            bronorganisatie=730924658,
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )

        self.assertEqual(
            eio.unique_representation(),
            "730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04",
        )

    def test_gebruiksrechten(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            bronorganisatie=730924658,
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )
        eio_url = reverse(eio)
        gebruiksrechten = GebruiksrechtenCMISFactory(
            informatieobject=eio_url, omschrijving_voorwaarden="some conditions"
        )

        self.assertEqual(
            gebruiksrechten.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - some conditions",
        )

    @tag("oio")
    def test_oio(self):
        self.create_zaak_besluit_services()
        zaak = self.create_zaak(**{"identificatie": 12345})
        eio = EnkelvoudigInformatieObjectFactory.create(
            bronorganisatie=730924658,
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
