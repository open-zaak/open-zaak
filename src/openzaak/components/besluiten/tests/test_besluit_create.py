from datetime import date

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse

from openzaak.components.catalogi.models.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.models.tests.factories import ZaakFactory
from openzaak.utils.tests import JWTAuthMixin

from ..constants import VervalRedenen
from ..models import Besluit
from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import get_operation_url


class BesluitCreateTests(TypeCheckMixin, JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    @freeze_time("2018-09-06T12:08+0200")
    def test_us162_voeg_besluit_toe_aan_zaak(self):
        zaak = ZaakFactory.create(zaaktype__concept=False)
        zaak_url = reverse(zaak)
        besluittype = BesluitTypeFactory.create()
        besluittype_url = reverse(besluittype)
        besluittype.zaaktypes.add(zaak.zaaktype)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = reverse(io)
        besluittype.informatieobjecttypes.add(io.informatieobjecttype)

        with self.subTest(part="besluit_create"):
            url = get_operation_url("besluit_create")

            response = self.client.post(
                url,
                {
                    "verantwoordelijke_organisatie": "517439943",  # RSIN
                    "identificatie": "123123",
                    "besluittype": f"http://testserver{besluittype_url}",
                    "zaak": f"http://testserver{zaak_url}",
                    "datum": "2018-09-06",
                    "toelichting": "Vergunning verleend.",
                    "ingangsdatum": "2018-10-01",
                    "vervaldatum": "2018-11-01",
                    "vervalreden": VervalRedenen.tijdelijk,
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            self.assertResponseTypes(
                response.data,
                (
                    ("url", str),
                    ("identificatie", str),
                    ("verantwoordelijke_organisatie", str),
                    ("besluittype", str),
                    ("zaak", str),
                    ("datum", str),
                    ("toelichting", str),
                    ("bestuursorgaan", str),
                    ("ingangsdatum", str),
                    ("vervaldatum", str),
                    ("vervalreden", str),
                    ("publicatiedatum", type(None)),
                    ("verzenddatum", type(None)),
                    ("uiterlijke_reactiedatum", type(None)),
                ),
            )

            self.assertEqual(Besluit.objects.count(), 1)

            besluit = Besluit.objects.get()
            self.assertEqual(besluit.verantwoordelijke_organisatie, "517439943")
            self.assertEqual(besluit.besluittype, besluittype)
            self.assertEqual(besluit.zaak, zaak)
            self.assertEqual(besluit.datum, date(2018, 9, 6))
            self.assertEqual(besluit.toelichting, "Vergunning verleend.")
            self.assertEqual(besluit.ingangsdatum, date(2018, 10, 1))
            self.assertEqual(besluit.vervaldatum, date(2018, 11, 1))
            self.assertEqual(besluit.vervalreden, VervalRedenen.tijdelijk)

        with self.subTest(part="besluitinformatieobject_create"):
            url = get_operation_url("besluitinformatieobject_create")

            response = self.client.post(
                url,
                {
                    "besluit": reverse(besluit),
                    "informatieobject": f"http://testserver{io_url}",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            self.assertResponseTypes(
                response.data, (("url", str), ("informatieobject", str))
            )

            self.assertEqual(besluit.besluitinformatieobject_set.count(), 1)
            self.assertEqual(
                besluit.besluitinformatieobject_set.get().informatieobject, io.canonical
            )

    def test_opvragen_informatieobjecten_besluit(self):
        besluit1, besluit2 = BesluitFactory.create_batch(2)

        besluit1_uri = reverse(besluit1)
        besluit2_uri = reverse(besluit2)

        BesluitInformatieObjectFactory.create_batch(3, besluit=besluit1)
        BesluitInformatieObjectFactory.create_batch(2, besluit=besluit2)

        base_uri = get_operation_url("besluitinformatieobject_list")

        url1 = f"{base_uri}?besluit={besluit1_uri}"
        response1 = self.client.get(url1)
        self.assertEqual(len(response1.data), 3)

        url2 = f"{base_uri}?besluit={besluit2_uri}"
        response2 = self.client.get(url2)
        self.assertEqual(len(response2.data), 2)

    def test_besluit_create_fail_besluittype_max_length(self):
        zaak = ZaakFactory.create(zaaktype__concept=False)
        zaak_url = reverse(zaak)

        url = get_operation_url("besluit_create")

        response = self.client.post(
            url,
            {
                "verantwoordelijke_organisatie": "517439943",  # RSIN
                "identificatie": "123123",
                "besluittype": f"http://testserver/{'x'*1000}",
                "zaak": f"http://testserver{zaak_url}",
                "datum": "2018-09-06",
                "toelichting": "Vergunning verleend.",
                "ingangsdatum": "2018-10-01",
                "vervaldatum": "2018-11-01",
                "vervalreden": VervalRedenen.tijdelijk,
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "besluittype")
        self.assertEqual(error["code"], "max_length")
