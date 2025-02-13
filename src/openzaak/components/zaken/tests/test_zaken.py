# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from copy import copy
from datetime import date, datetime

from django.contrib.gis.geos import Point
from django.test import override_settings, tag
from django.utils import timezone

import requests_mock
from dateutil.relativedelta import relativedelta
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie,
    Archiefstatus,
    BrondatumArchiefprocedureAfleidingswijze,
    ComponentTypes,
    RolOmschrijving,
    RolTypes,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import get_validation_errors, reverse
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.catalogi.tests.factories import (
    ResultaatTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.tests.utils import JWTAuthMixin, mock_ztc_oas_get

from ..api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
    SCOPEN_ZAKEN_HEROPENEN,
)
from ..constants import BetalingsIndicatie
from ..models import (
    Medewerker,
    NatuurlijkPersoon,
    NietNatuurlijkPersoon,
    OrganisatorischeEenheid,
    Vestiging,
    Zaak,
    ZaakIdentificatie,
)
from .constants import POLYGON_AMSTERDAM_CENTRUM
from .factories import ResultaatFactory, RolFactory, StatusFactory, ZaakFactory
from .utils import (
    ZAAK_READ_KWARGS,
    ZAAK_WRITE_KWARGS,
    get_catalogus_response,
    get_operation_url,
    get_zaaktype_response,
    isodatetime,
    utcdatetime,
)


class ApiStrategyTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_api_44_crs_headers(self):
        # We wijken bewust af - EPSG:4326 is de standaard projectie voor WGS84
        # De andere opties in de API strategie lijken in de praktijk niet/nauwelijks
        # gebruikt te worden, en zien er vreemd uit t.o.v. wel courant gebruikte
        # opties.
        zaak = ZaakFactory.create(zaakgeometrie=Point(4.887990, 52.377595))  # LONG LAT
        url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_412_PRECONDITION_FAILED)

        response = self.client.get(url, headers={"accept-crs": "dummy"})
        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)

        response = self.client.get(url, headers={"accept-crs": "EPSG:4326"})
        self.assertEqual(response["Content-Crs"], "EPSG:4326")

    def test_api_51_status_codes(self):
        with self.subTest(crud="create"):
            zaaktype = ZaakTypeFactory.create(concept=False)
            zaaktype_url = reverse(zaaktype)
            url = reverse("zaak-list")

            response = self.client.post(
                url,
                {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-06-11",
                    "startdatum": "2018-06-11",
                },
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response["Location"], response.data["url"])

        with self.subTest(crud="read"):
            response_detail = self.client.get(response.data["url"], **ZAAK_READ_KWARGS)
            self.assertEqual(response_detail.status_code, status.HTTP_200_OK)


class ZakenAfsluitenTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_zaak_afsluiten(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})
        statustype1 = StatusTypeFactory.create(zaaktype=zaaktype)
        statustype1_url = reverse(statustype1)
        statustype2 = StatusTypeFactory.create(zaaktype=zaaktype)
        statustype2_url = reverse(statustype2)
        resultaattype = ResultaatTypeFactory.create(
            zaaktype=zaaktype,
            archiefactietermijn=relativedelta(years=10),
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
        )
        resultaattype_url = reverse(resultaattype)

        # Set initial status
        status_list_url = reverse("status-list")

        response = self.client.post(
            status_list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{statustype1_url}",
                "datumStatusGezet": isodatetime(2018, 10, 1, 10, 00, 00),
            },
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        zaak.refresh_from_db()
        self.assertIsNone(zaak.einddatum)

        # add a result for the case
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Set eindstatus
        datum_status_gezet = utcdatetime(2018, 10, 22, 10, 00, 00)

        response = self.client.post(
            status_list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{statustype2_url}",
                "datumStatusGezet": datum_status_gezet.isoformat(),
            },
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        zaak.refresh_from_db()
        self.assertEqual(zaak.einddatum, datum_status_gezet.date())
        self.assertEqual(
            zaak.archiefactiedatum, zaak.einddatum + relativedelta(years=10)
        )

    def test_close_zaak_not_in_utc(self):
        """
        imagine that the client timezone is +2:00 and we create and close
        zaak at ~2023-01-01T00:00:00+2:00
        freeze_gun is not used here, because it doesn't seem to work correctly
        with timezones
        """
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaak = ZaakFactory.create(zaaktype=zaaktype, startdatum="2023-01-01")
        zaak_url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})
        statustype = StatusTypeFactory.create(zaaktype=zaaktype)
        resultaattype = ResultaatTypeFactory.create(
            zaaktype=zaaktype,
            archiefactietermijn=relativedelta(years=10),
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
        )
        ResultaatFactory(zaak=zaak, resultaattype=resultaattype)
        statustype_url = reverse(statustype)
        status_list_url = reverse("status-list")

        response = self.client.post(
            status_list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{statustype_url}",
                "datumStatusGezet": datetime.fromisoformat("2023-01-01 00:00:00+02:00"),
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        zaak.refresh_from_db()
        self.assertEqual(zaak.einddatum, date(2023, 1, 1))


class ZakenTests(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_ALLES_LEZEN]
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype_url = reverse(cls.zaaktype)
        cls.statustype = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_url = reverse(cls.statustype)
        cls.statustype2 = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype2_url = reverse(cls.statustype2)

        super().setUpTestData()

    def test_enkel_initiele_status_met_scope_aanmaken(self):
        """
        Met de scope zaken.aanmaken mag je enkel een status aanmaken als er
        nog geen status was.
        """
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaak_url = reverse(zaak)
        status_list_url = reverse("status-list")

        # initiele status
        response = self.client.post(
            status_list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_url}",
                "datumStatusGezet": isodatetime(2018, 10, 1, 10, 00, 00),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # extra status - mag niet, onafhankelijk van de data
        response = self.client.post(
            status_list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_url}",
                "datumStatusGezet": isodatetime(2018, 10, 2, 10, 00, 00),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(zaak.status_set.count(), 1)

    def test_zaak_heropen_reset_einddatum(self):
        self.autorisatie.scopes = self.autorisatie.scopes + [SCOPEN_ZAKEN_HEROPENEN]
        self.autorisatie.save()

        zaak = ZaakFactory.create(einddatum=date(2019, 1, 7), zaaktype=self.zaaktype)
        StatusFactory.create(
            zaak=zaak,
            statustype=self.statustype2,
            datum_status_gezet="2019-01-07T12:51:41+0000",
        )
        zaak_url = reverse(zaak)
        status_list_url = reverse("status-list")

        # Set status other than eindstatus
        datum_status_gezet = utcdatetime(2019, 1, 7, 12, 53, 25)
        response = self.client.post(
            status_list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{self.statustype_url}",
                "datumStatusGezet": datum_status_gezet.isoformat(),
            },
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        zaak.refresh_from_db()
        self.assertIsNone(zaak.einddatum)

    def test_zaak_create_fail_zaaktype_maxlength(self):
        """
        Assert that the default vertrouwelijkheidaanduiding is set.
        """
        self.applicatie.heeft_alle_autorisaties = True
        self.applicatie.save()

        url = reverse("zaak-list")
        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver/{'x'*1000}",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "zaaktype")
        self.assertEqual(error["code"], "max_length")

    def test_zaak_met_producten(self):
        url = reverse("zaak-list")
        self.zaaktype.producten_of_diensten = [
            "https://example.com/product/123",
            "https://example.com/dienst/123",
        ]
        self.zaaktype.save()

        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver{self.zaaktype_url}",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
                "productenOfDiensten": ["https://example.com/product/123"],
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        zaak = Zaak.objects.get()
        self.assertEqual(len(zaak.producten_of_diensten), 1)

        # update
        response2 = self.client.patch(
            response.data["url"],
            {
                "productenOfDiensten": [
                    "https://example.com/product/123",
                    "https://example.com/dienst/123",
                ]
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        zaak.refresh_from_db()
        self.assertEqual(len(zaak.producten_of_diensten), 2)

    def test_zaak_vertrouwelijkheidaanduiding_afgeleid(self):
        """
        Assert that the default vertrouwelijkheidaanduiding is set.
        """
        url = reverse("zaak-list")
        self.zaaktype.vertrouwelijkheidaanduiding = (
            VertrouwelijkheidsAanduiding.zaakvertrouwelijk
        )
        self.zaaktype.save()

        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver{self.zaaktype_url}",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.zaakvertrouwelijk,
        )

    def test_zaak_vertrouwelijkheidaanduiding_expliciet(self):
        """
        Assert that the default vertrouwelijkheidaanduiding is set.
        """
        url = reverse("zaak-list")
        self.zaaktype.vertrouwelijkheidaanduiding = (
            VertrouwelijkheidsAanduiding.zaakvertrouwelijk
        )
        self.zaaktype.save()

        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver{self.zaaktype_url}",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.openbaar,
        )

    def test_deelzaken(self):
        hoofdzaak = ZaakFactory.create(zaaktype=self.zaaktype)
        deelzaak = ZaakFactory.create(hoofdzaak=hoofdzaak, zaaktype=self.zaaktype)
        detail_url = reverse(hoofdzaak)
        deelzaak_url = reverse(deelzaak)

        response = self.client.get(detail_url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["deelzaken"], [f"http://testserver{deelzaak_url}"]
        )

    def test_create_deelzaak_success(self, *mocks):
        zaaktype2 = ZaakTypeFactory.create(concept=False)
        zaaktype2_url = f"http://testserver{reverse(zaaktype2)}"
        self.zaaktype.deelzaaktypen.add(zaaktype2)
        hoofdzaak = ZaakFactory.create(zaaktype=self.zaaktype)
        autorisatie = copy(self.autorisatie)
        autorisatie.pk = None
        autorisatie.zaaktype = zaaktype2_url
        autorisatie.save()
        detail_url = reverse(hoofdzaak)

        response = self.client.post(
            reverse("zaak-list"),
            {
                "zaaktype": zaaktype2_url,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "hoofdzaak": f"http://testserver{detail_url}",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-06-11",
                "startdatum": "2018-06-11",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Zaak.objects.count(), 2)

    def test_zaak_betalingsindicatie_nvt(self):
        zaak = ZaakFactory.create(
            betalingsindicatie=BetalingsIndicatie.gedeeltelijk,
            laatste_betaaldatum=timezone.now(),
            zaaktype=self.zaaktype,
        )
        url = reverse(zaak)

        response = self.client.patch(
            url, {"betalingsindicatie": BetalingsIndicatie.nvt}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["laatsteBetaaldatum"], None)
        zaak.refresh_from_db()
        self.assertIsNone(zaak.laatste_betaaldatum)

    def test_pagination_default(self):
        ZaakFactory.create_batch(2, zaaktype=self.zaaktype)
        url = reverse(Zaak)

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        ZaakFactory.create_batch(2, zaaktype=self.zaaktype)
        url = reverse(Zaak)

        response = self.client.get(url, {"page": 1}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_complex_geometry(self):
        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver{self.zaaktype_url}",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
                "zaakgeometrie": {
                    "type": "Polygon",
                    "coordinates": [POLYGON_AMSTERDAM_CENTRUM],
                },
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.json()["zaakgeometrie"])
        zaak = Zaak.objects.get()
        self.assertIsNotNone(zaak.zaakgeometrie)

    @tag("gh-1108")
    def test_create_zaak_with_archived_archivation_status(self):
        """
        Regression test for creating a zaak with with an archivation status.

        https://github.com/open-zaak/open-zaak/issues/1108
        """
        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "zaaktype": f"http://testserver{self.zaaktype_url}",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
                "archiefstatus": Archiefstatus.gearchiveerd_procestermijn_onbekend,
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @tag("gh-1228")
    def test_correct_zaak_verlenging_when_empty(self):
        zaak = ZaakFactory.create(
            verlenging_reden="", verlenging_duur=None, zaaktype=self.zaaktype
        )
        detail_url = reverse(zaak)

        response = self.client.get(detail_url, **ZAAK_READ_KWARGS)

        self.assertIsNone(response.json()["verlenging"])

    @tag("gh-1228")
    def test_correct_zaak_verlenging_when_set(self):
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            verlenging_reden="Een reden",
            verlenging_duur=relativedelta(days=5),
        )
        detail_url = reverse(zaak)

        response = self.client.get(detail_url, **ZAAK_READ_KWARGS)

        self.assertEqual(
            response.json()["verlenging"], {"reden": "Een reden", "duur": "P5D"}
        )

    def test_create_zaak_with_processobject(self):
        url = reverse(Zaak)
        zaak_data = {
            "zaaktype": f"http://testserver{self.zaaktype_url}",
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-12-24",
            "startdatum": "2018-12-24",
            "processobjectaard": "test object",
            "startdatumBewaartermijn": "2019-08-24",
            "processobject": {
                "datumkenmerk": "test data",
                "identificatie": "12345",
                "objecttype": "test type",
                "registratie": "test registration",
            },
        }

        response = self.client.post(url, zaak_data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak = Zaak.objects.get()

        self.assertEqual(zaak.processobjectaard, "test object")
        self.assertEqual(zaak.startdatum_bewaartermijn, date(2019, 8, 24))
        self.assertEqual(zaak.processobject_datumkenmerk, "test data")
        self.assertEqual(zaak.processobject_identificatie, "12345")
        self.assertEqual(zaak.processobject_objecttype, "test type")
        self.assertEqual(zaak.processobject_registratie, "test registration")

    def test_sort_datum_ascending(self):
        sorting_params = [
            "startdatum",
            "einddatum",
            "publicatiedatum",
            "archiefactiedatum",
            "registratiedatum",
        ]

        for param in sorting_params:
            with self.subTest(param=param):
                Zaak.objects.all().delete()
                ZaakFactory.create(**{param: date(2019, 1, 1)}, zaaktype=self.zaaktype)
                ZaakFactory.create(**{param: date(2019, 3, 1)}, zaaktype=self.zaaktype)
                ZaakFactory.create(**{param: date(2019, 2, 1)}, zaaktype=self.zaaktype)
                url = reverse("zaak-list")

                response = self.client.get(url, {"ordering": param}, **ZAAK_READ_KWARGS)

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.data["results"]

                self.assertEqual(data[0][param], "2019-01-01")
                self.assertEqual(data[1][param], "2019-02-01")
                self.assertEqual(data[2][param], "2019-03-01")

    def test_sort_datum_descending(self):
        sorting_params = [
            "startdatum",
            "einddatum",
            "publicatiedatum",
            "archiefactiedatum",
            "registratiedatum",
        ]

        for param in sorting_params:
            with self.subTest(param=param):
                Zaak.objects.all().delete()
                ZaakFactory.create(**{param: date(2019, 1, 1)}, zaaktype=self.zaaktype)
                ZaakFactory.create(**{param: date(2019, 3, 1)}, zaaktype=self.zaaktype)
                ZaakFactory.create(**{param: date(2019, 2, 1)}, zaaktype=self.zaaktype)
                url = reverse("zaak-list")

                response = self.client.get(
                    url, {"ordering": f"-{param}"}, **ZAAK_READ_KWARGS
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.data["results"]

                self.assertEqual(data[0][param], "2019-03-01")
                self.assertEqual(data[1][param], "2019-02-01")
                self.assertEqual(data[2][param], "2019-01-01")

    def test_sort_identificatie(self):
        ZaakFactory.create(identificatie="ZAAK1", zaaktype=self.zaaktype)
        ZaakFactory.create(identificatie="ZAAK2", zaaktype=self.zaaktype)
        url = reverse("zaak-list")

        with self.subTest(param="identificatie"):
            response = self.client.get(
                url, {"ordering": "identificatie"}, **ZAAK_READ_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["results"][0]["identificatie"], "ZAAK1")
            self.assertEqual(response.json()["results"][1]["identificatie"], "ZAAK2")

        with self.subTest(param="-identificatie"):
            response = self.client.get(
                url, {"ordering": "-identificatie"}, **ZAAK_READ_KWARGS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["results"][0]["identificatie"], "ZAAK2")
            self.assertEqual(response.json()["results"][1]["identificatie"], "ZAAK1")

    @tag("gh-1511")
    def test_create_zaak_with_incorrect_local_zaaktype(self):
        url = reverse(Zaak)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": uuid.uuid4()})

        zaak_data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-12-24",
            "startdatum": "2018-12-24",
            "processobjectaard": "test object",
            "startdatumBewaartermijn": "2019-08-24",
        }

        response = self.client.post(url, zaak_data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "zaaktype")
        self.assertEqual(error["code"], "does_not_exist")

    @tag("gh-1836")
    def test_reserve_zaak_identity(self):

        data = {"bronorganisatie": "111222333"}

        response = self.client.post(reverse("zaakidentificatie-list"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Zaak.objects.count(), 0)
        self.assertEqual(ZaakIdentificatie.objects.count(), 1)

        zaak_identificatie = ZaakIdentificatie.objects.get()
        self.assertEqual(
            response.json(), {"zaaknummer": zaak_identificatie.identificatie}
        )

        zaak_id = response.json()["zaaknummer"]
        zaak_data = {
            "zaaktype": f"http://testserver{self.zaaktype_url}",
            "identificatie": zaak_id,
            "bronorganisatie": "111222333",
            "verantwoordelijkeOrganisatie": "111222333",
            "startdatum": "2025-02-05",
        }

        create_response = self.client.post(
            reverse("zaak-list"), zaak_data, **ZAAK_WRITE_KWARGS
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Zaak.objects.count(), 1)
        self.assertEqual(ZaakIdentificatie.objects.count(), 1)

        # try to reuse id
        zaak_data_2 = {
            "zaaktype": f"http://testserver{self.zaaktype_url}",
            "identificatie": zaak_id,
            "bronorganisatie": "111222333",
            "verantwoordelijkeOrganisatie": "111222333",
            "startdatum": "2025-02-07",
        }

        create_response_2 = self.client.post(
            reverse("zaak-list"), zaak_data_2, **ZAAK_WRITE_KWARGS
        )
        self.assertEqual(create_response_2.status_code, status.HTTP_400_BAD_REQUEST)

    @tag("gh-1836")
    def test_reserve_zaak_identity_with_different_bronorganisatie(self):

        data = {"bronorganisatie": "111222333"}

        response = self.client.post(reverse("zaakidentificatie-list"), data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Zaak.objects.count(), 0)
        self.assertEqual(ZaakIdentificatie.objects.count(), 1)

        reserved_zaak_id = ZaakIdentificatie.objects.get()

        zaaknummer = response.data["zaaknummer"]
        zaak_data = {
            "zaaktype": f"http://testserver{self.zaaktype_url}",
            "identificatie": zaaknummer,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "startdatum": "2025-02-04",
        }

        create_response = self.client.post(
            reverse("zaak-list"), zaak_data, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Zaak.objects.count(), 1)
        self.assertEqual(ZaakIdentificatie.objects.count(), 2)

        zaak = Zaak.objects.get()
        self.assertEqual(zaak.identificatie, zaaknummer)
        self.assertNotEqual(zaak.identificatie_ptr, reserved_zaak_id)


class ZakenFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_rol_nnp_id(self):
        url = reverse(Zaak)
        rol = RolFactory.create(
            betrokkene_type=RolTypes.niet_natuurlijk_persoon,
            omschrijving_generiek=RolOmschrijving.initiator,
        )
        NietNatuurlijkPersoon.objects.create(rol=rol, inn_nnp_id="129117729")

        with self.subTest(expected="no-match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__innNnpId": "000000000"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 0)

        with self.subTest(expected="match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__innNnpId": "129117729"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)

    def test_rol_nnp_ann_identificatie(self):
        url = reverse(Zaak)
        rol = RolFactory.create(
            betrokkene_type=RolTypes.niet_natuurlijk_persoon,
            omschrijving_generiek=RolOmschrijving.initiator,
        )
        NietNatuurlijkPersoon.objects.create(rol=rol, ann_identificatie="12345")

        with self.subTest(expected="no-match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__annIdentificatie": "000000000"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 0)

        with self.subTest(expected="match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__nietNatuurlijkPersoon__annIdentificatie": "12345"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)

    def test_rol_np_anp_identificatie(self):
        url = reverse(Zaak)
        rol = RolFactory.create(
            betrokkene_type=RolTypes.natuurlijk_persoon,
            omschrijving_generiek=RolOmschrijving.initiator,
        )
        NatuurlijkPersoon.objects.create(rol=rol, anp_identificatie="12345")

        with self.subTest(expected="no-match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__natuurlijkPersoon__anpIdentificatie": "000000000"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 0)

        with self.subTest(expected="match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__natuurlijkPersoon__anpIdentificatie": "12345"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)

    def test_rol_np_inp_a_nummer(self):
        url = reverse(Zaak)
        rol = RolFactory.create(
            betrokkene_type=RolTypes.natuurlijk_persoon,
            omschrijving_generiek=RolOmschrijving.initiator,
        )
        NatuurlijkPersoon.objects.create(rol=rol, inp_a_nummer="12345")

        with self.subTest(expected="no-match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__natuurlijkPersoon__inpA_nummer": "000000000"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 0)

        with self.subTest(expected="match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__natuurlijkPersoon__inpA_nummer": "12345"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)

    def test_rol_vestiging_vestigings_nummer(self):
        url = reverse(Zaak)
        rol = RolFactory.create(
            betrokkene_type=RolTypes.vestiging,
            omschrijving_generiek=RolOmschrijving.initiator,
        )
        Vestiging.objects.create(rol=rol, vestigings_nummer="12345")

        with self.subTest(expected="no-match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__vestiging__vestigingsNummer": "000000000"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 0)

        with self.subTest(expected="match"):
            response = self.client.get(
                url,
                {"rol__betrokkeneIdentificatie__vestiging__vestigingsNummer": "12345"},
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)


class ZaakArchivingTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_zaak_archiefactiedatum_afleidingswijze_ingangsdatum_besluit(self):
        zaaktype = ZaakTypeFactory.create()
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        zaak_url = reverse(zaak)
        statustype1 = StatusTypeFactory.create(zaaktype=zaaktype)
        statustype1_url = reverse(statustype1)
        statustype2 = StatusTypeFactory.create(zaaktype=zaaktype)
        statustype2_url = reverse(statustype2)
        resultaattype = ResultaatTypeFactory.create(
            zaaktype=zaaktype,
            archiefactietermijn=relativedelta(years=10),
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.ingangsdatum_besluit,
        )
        resultaattype_url = reverse(resultaattype)

        BesluitFactory.create(zaak=zaak, ingangsdatum="2020-05-03")

        # Set initial status
        status_list_url = reverse("status-list")

        response = self.client.post(
            status_list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{statustype1_url}",
                "datumStatusGezet": isodatetime(2018, 10, 1, 10, 00, 00),
            },
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        zaak.refresh_from_db()
        self.assertIsNone(zaak.einddatum)

        # add a result for the case
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {
            "zaak": zaak_url,
            "resultaattype": f"http://testserver{resultaattype_url}",
            "toelichting": "",
        }

        response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Set eindstatus
        datum_status_gezet = utcdatetime(2018, 10, 22, 10, 00, 00)

        response = self.client.post(
            status_list_url,
            {
                "zaak": zaak_url,
                "statustype": f"http://testserver{statustype2_url}",
                "datumStatusGezet": datum_status_gezet.isoformat(),
            },
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        zaak.refresh_from_db()
        self.assertEqual(zaak.einddatum, datum_status_gezet.date())
        self.assertEqual(
            zaak.archiefactiedatum, date(2030, 5, 3)  # 2020-05-03 + 10 years
        )


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakCreateExternalURLsTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = get_operation_url("zaak_create")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

    def test_create_external_zaaktype(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
            m.get(zaaktype, json=get_zaaktype_response(catalogus, zaaktype))
            m.get(catalogus, json=get_catalogus_response(catalogus, zaaktype))

            response = self.client.post(
                self.list_url,
                {
                    "zaaktype": zaaktype,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                },
                **ZAAK_WRITE_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_create_external_zaaktype_fail_bad_url(self):
        response = self.client.post(
            self.list_url,
            {
                "zaaktype": "abcd",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "zaaktype")
        self.assertEqual(error["code"], "bad-url")

    def test_create_external_zaaktype_fail_not_json_url(self):
        ServiceFactory.create(api_root="http://example.com/", api_type=APITypes.ztc)
        with requests_mock.Mocker() as m:
            m.get("http://example.com/", status_code=200, text="<html></html>")
            response = self.client.post(
                self.list_url,
                {
                    "zaaktype": "http://example.com/",
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                },
                **ZAAK_WRITE_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "zaaktype")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_zaaktype_fail_invalid_schema(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
            m.get(
                zaaktype,
                json={
                    "url": zaaktype,
                    "catalogus": catalogus,
                    "identificatie": "12345",
                    "omschrijving": "Main zaaktype",
                    "vertrouwelijkheidaanduiding": "openbaar",
                    "concept": False,
                },
            )
            m.get(
                catalogus,
                json=get_catalogus_response(catalogus, zaaktype),
            )

            response = self.client.post(
                self.list_url,
                {
                    "zaaktype": zaaktype,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                },
                **ZAAK_WRITE_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "zaaktype")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_zaaktype_fail_not_published(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"

        zaaktype_data = get_zaaktype_response(catalogus, zaaktype)
        zaaktype_data["concept"] = True

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
            m.get(zaaktype, json=zaaktype_data)
            m.get(catalogus, json=get_catalogus_response(catalogus, zaaktype))

            response = self.client.post(
                self.list_url,
                {
                    "zaaktype": zaaktype,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                },
                **ZAAK_WRITE_KWARGS,
            )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "zaaktype")
        self.assertEqual(error["code"], "not-published")

    def test_create_external_zaaktype_fail_unknown_service(self):
        response = self.client.post(
            self.list_url,
            {
                "zaaktype": "https://other-externe.catalogus.nl/api/v1/zaaktypen/1",
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "zaaktype")
        self.assertEqual(error["code"], "unknown-service")


class ZakenWerkVoorraadTests(JWTAuthMixin, APITestCase):
    """
    Test that the queries to build up a 'werkvoorraad' work as expected.
    """

    heeft_alle_autorisaties = True

    def test_rol_medewerker_url(self):
        """
        Test that zaken for a specific medewerker can be retrieved.
        """
        url = reverse(Zaak)
        MEDEWERKER = "https://medewerkers.nl/api/v1/medewerkers/1"
        rol1 = RolFactory.create(
            betrokkene=MEDEWERKER,
            betrokkene_type=RolTypes.medewerker,
            omschrijving_generiek=RolOmschrijving.behandelaar,
        )
        rol2 = RolFactory.create(
            betrokkene_type=RolTypes.medewerker,
            omschrijving_generiek=RolOmschrijving.behandelaar,
        )
        RolFactory.create(
            betrokkene_type=RolTypes.natuurlijk_persoon,
            omschrijving_generiek=RolOmschrijving.initiator,
        )
        zaak1, zaak2 = rol1.zaak, rol2.zaak

        with self.subTest(filter_on="betrokkeneType"):
            query = {"rol__betrokkeneType": RolTypes.medewerker}

            response = self.client.get(url, query, **ZAAK_READ_KWARGS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 2)
            urls = {result["url"] for result in response.data["results"]}
            self.assertEqual(
                urls,
                {
                    f"http://testserver{reverse(zaak1)}",
                    f"http://testserver{reverse(zaak2)}",
                },
            )

        with self.subTest(filter_on="omschrijving generiek"):
            query = {"rol__omschrijvingGeneriek": RolOmschrijving.behandelaar}

            response = self.client.get(url, query, **ZAAK_READ_KWARGS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 2)
            urls = {result["url"] for result in response.data["results"]}
            self.assertEqual(
                urls,
                {
                    f"http://testserver{reverse(zaak1)}",
                    f"http://testserver{reverse(zaak2)}",
                },
            )

        with self.subTest(filter_on="betrokkene"):
            query = {"rol__betrokkene": MEDEWERKER}

            response = self.client.get(url, query, **ZAAK_READ_KWARGS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)
            self.assertEqual(
                response.data["results"][0]["url"],
                f"http://testserver{reverse(zaak1)}",
            )

    def test_rol_medewerker_identificatie(self):
        url = reverse(Zaak)
        rol = RolFactory.create(
            betrokkene_type=RolTypes.medewerker,
            omschrijving_generiek=RolOmschrijving.behandelaar,
        )
        Medewerker.objects.create(
            rol=rol,
            identificatie="some-username",
        )

        with self.subTest(expected="no-match"):
            response = self.client.get(
                url,
                {"rol__betrokkeneIdentificatie__medewerker__identificatie": "no-match"},
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 0)

        with self.subTest(expected="match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__medewerker__identificatie": "some-username"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)

    def test_rol_np_bsn(self):
        """
        Essential to be able to fetch all Zaken related to a particular citizen.
        """
        url = reverse(Zaak)
        rol = RolFactory.create(
            betrokkene_type=RolTypes.natuurlijk_persoon,
            omschrijving_generiek=RolOmschrijving.initiator,
        )
        NatuurlijkPersoon.objects.create(
            rol=rol, inp_bsn="129117729"
        )  # http://www.wilmans.com/sofinummer/

        with self.subTest(expected="no-match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": "000000000"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 0)

        with self.subTest(expected="match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": "129117729"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)

    def test_rol_organisatorische_eenheid_identificatie(self):
        """
        Test filter zaken on betrokkeneIdentificatie for Organisatorische Eenheid.
        """
        url = reverse(Zaak)
        rol = RolFactory.create(
            betrokkene_type=RolTypes.organisatorische_eenheid,
            omschrijving_generiek=RolOmschrijving.behandelaar,
        )
        OrganisatorischeEenheid.objects.create(identificatie="OE1", rol=rol)

        with self.subTest(expected="no-match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__organisatorischeEenheid__identificatie": "123"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 0)

        with self.subTest(expected="match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__organisatorischeEenheid__identificatie": "OE1"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)
