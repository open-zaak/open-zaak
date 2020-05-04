from django.conf import settings
from django.test import tag

from vng_api_common.tests import reverse

from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.utils.tests import APITestCaseCMIS

from ...models import ObjectInformatieObject
from ..factories import (
    EnkelvoudigInformatieObjectFactory,
    GebruiksrechtenCMISFactory,
    GebruiksrechtenFactory,
)


class UniqueRepresentationTestCase(APITestCaseCMIS):
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
        if settings.CMIS_ENABLED:
            eio = EnkelvoudigInformatieObjectFactory.create(
                bronorganisatie=730924658,
                identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
            )
            eio_url = reverse(eio)
            gebruiksrechten = GebruiksrechtenCMISFactory(
                informatieobject=eio_url, omschrijving_voorwaarden="some conditions"
            )
        else:
            gebruiksrechten = GebruiksrechtenFactory(
                informatieobject__latest_version__bronorganisatie=730924658,
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
            bronorganisatie=730924658,
            identificatie="5d940d52-ff5e-4b18-a769-977af9130c04",
        )
        eio_url = f"http://testserver{reverse(eio)}"

        if settings.CMIS_ENABLED:
            oio = ObjectInformatieObject.objects.create(
                informatieobject=eio_url, zaak=zaak, object_type="zaak"
            )
        else:
            oio = ObjectInformatieObject.objects.create(
                zaak=zaak, object_type="zaak", informatieobject=eio.canonical
            )

        self.assertEqual(
            oio.unique_representation(),
            "(730924658 - 5d940d52-ff5e-4b18-a769-977af9130c04) - 12345",
        )
