# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from datetime import date

from django.contrib.sites.models import Site
from django.test import override_settings

from freezegun import freeze_time
from rest_framework import status
from vng_api_common.tests import TypeCheckMixin, reverse

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from ...zaken.tests.factories import ZaakFactory
from ..constants import VervalRedenen
from ..models import Besluit
from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import get_operation_url


@require_cmis
@override_settings(CMIS_ENABLED=True)
class BesluitCreateCMISTests(TypeCheckMixin, JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    @freeze_time("2018-09-06T12:08+0200")
    def test_us162_voeg_besluit_toe_aan_zaak(self):
        zaak = ZaakFactory.create(zaaktype__concept=False)
        zaak_url = reverse(zaak)
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        besluittype.zaaktypen.add(zaak.zaaktype)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = reverse(io)
        besluittype.informatieobjecttypen.add(io.informatieobjecttype)

        # Mocking the besluit
        besluit_data = {
            "verantwoordelijke_organisatie": "517439943",  # RSIN
            "identificatie": "123123",
            "besluittype": f"http://testserver{besluittype_url}",
            "zaak": f"http://testserver{zaak_url}",
            "datum": "2018-09-06",
            "toelichting": "Vergunning verleend.",
            "ingangsdatum": "2018-10-01",
            "vervaldatum": "2018-11-01",
            "vervalreden": VervalRedenen.tijdelijk,
        }

        with self.subTest(part="besluit_create"):
            url = get_operation_url("besluit_create")

            response = self.client.post(url, besluit_data)

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
                    "besluit": f"http://testserver{reverse(besluit)}",
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
                besluit.besluitinformatieobject_set.get().informatieobject.uuid,
                io.uuid,
            )

    @override_settings(ALLOWED_HOSTS=["testserver", "example.com"])
    def test_opvragen_informatieobjecten_besluit(self):
        besluit1 = BesluitFactory.create()
        besluit2 = BesluitFactory.create()

        besluit1_uri = reverse(besluit1)
        besluit2_uri = reverse(besluit2)

        for counter in range(3):
            eio = EnkelvoudigInformatieObjectFactory.create()
            eio_url = eio.get_url()

            BesluitInformatieObjectFactory.create(
                besluit=besluit1, informatieobject=eio_url
            )

        for counter in range(2):
            eio = EnkelvoudigInformatieObjectFactory.create()
            eio_url = eio.get_url()

            BesluitInformatieObjectFactory.create(
                besluit=besluit2, informatieobject=eio_url
            )

        base_uri = get_operation_url("besluitinformatieobject_list")

        response1 = self.client.get(
            base_uri,
            {"besluit": f"http://example.com{besluit1_uri}"},
            headers={"host": "example.com"},
        )
        self.assertEqual(len(response1.data), 3)

        response2 = self.client.get(
            base_uri,
            {"besluit": f"http://example.com{besluit2_uri}"},
            headers={"host": "example.com"},
        )
        self.assertEqual(len(response2.data), 2)
