# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import tag

from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.zaken.tests.factories import ZaakFactory

from ...models import ObjectInformatieObject
from ..factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenFactory


class UniqueRepresentationTestCase(APITestCase):
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
        gebruiksrechten = GebruiksrechtenFactory(
            informatieobject__latest_version__bronorganisatie="730924658",
            informatieobject__latest_version__identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
            omschrijving_voorwaarden="some conditions",
        )

        self.assertEqual(
            gebruiksrechten.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - some conditions",
        )

    @tag("oio")
    def test_oio(self):
        zaak = ZaakFactory.create(identificatie="12345")
        eio = EnkelvoudigInformatieObjectFactory.create(
            bronorganisatie="730924658",
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )

        oio = ObjectInformatieObject.objects.create(
            zaak=zaak, object_type="zaak", informatieobject=eio.canonical
        )

        self.assertEqual(
            oio.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 12345",
        )

    @tag("oio", "external-urls")
    def test_oio_with_verzoek(self):
        ServiceFactory.create(
            api_root="https://extern.vrc.nl/api/v1/", api_type=APITypes.vrc
        )
        eio = EnkelvoudigInformatieObjectFactory.create(
            bronorganisatie="730924658",
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )

        oio = ObjectInformatieObject.objects.create(
            informatieobject=eio.canonical,
            verzoek="https://extern.vrc.nl/api/v1/verzoeken/123",
            object_type="verzoek",
        )

        # not a model we can generate a representation for -> take the last fragment
        # of the API URL
        self.assertEqual(
            oio.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 123",
        )
