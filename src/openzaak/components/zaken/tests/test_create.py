# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import threading
import time
import uuid
from datetime import date
from unittest.mock import patch

from django.db import close_old_connections, transaction
from django.test import override_settings, tag

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from vng_api_common.constants import (
    ComponentTypes,
    RolOmschrijving,
    VertrouwelijkheidsAanduiding,
    ZaakobjectTypes,
)
from vng_api_common.oas import fetcher
from vng_api_common.tests import get_validation_errors, reverse
from vng_api_common.utils import generate_unique_identification

from openzaak.components.catalogi.tests.factories import (
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
)
from openzaak.notifications.tests.mixins import NotificationsConfigMixin
from openzaak.tests.utils import ClearCachesMixin, JWTAuthMixin

from ..api.scopes import SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_CREATE
from ..api.viewsets import ZaakViewSet
from ..models import KlantContact, Rol, Status, Zaak, ZaakIdentificatie, ZaakObject
from .factories import ZaakFactory
from .utils import ZAAK_WRITE_KWARGS, get_operation_url, isodatetime

VERANTWOORDELIJKE_ORGANISATIE = "517439943"
OBJECT_MET_ADRES = f"https://example.com/orc/api/v1/objecten/{uuid.uuid4().hex}"
# Stadsdeel is een WijkObject in het RSGB
STADSDEEL = f"https://example.com/rsgb/api/v1/wijkobjecten/{uuid.uuid4().hex}"


class CreateZaakTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_create_zaak(self):
        """
        Maak een zaak van een bepaald type.
        """
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
            "toelichting": "Een stel dronken toeristen speelt versterkte "
            "muziek af vanuit een gehuurde boot.",
            "zaakgeometrie": {
                "type": "Point",
                "coordinates": [4.910649523925713, 52.37240093589432],
            },
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.json()
        self.assertIn("identificatie", data)

        # verify that the identification has been generated
        self.assertIsInstance(data["identificatie"], str)
        self.assertNotEqual(data["identificatie"], "")
        self.assertIsInstance(data["zaakgeometrie"], dict)  # geojson object

        zaak = Zaak.objects.get()
        self.assertEqual(zaak.zaaktype, zaaktype)
        self.assertEqual(zaak.registratiedatum, date(2018, 6, 11))
        self.assertEqual(
            zaak.toelichting,
            "Een stel dronken toeristen speelt versterkte "
            "muziek af vanuit een gehuurde boot.",
        )
        self.assertEqual(zaak.zaakgeometrie.x, 4.910649523925713)
        self.assertEqual(zaak.zaakgeometrie.y, 52.37240093589432)

    def test_create_zaak_zonder_bronorganisatie(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "registratiedatum": "2018-06-11",
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "bronorganisatie")
        self.assertEqual(error["code"], "required")

    def test_create_zaak_invalide_rsin(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "bronorganisatie": "123456789",
            "registratiedatum": "2018-06-11",
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "bronorganisatie")
        self.assertEqual(error["code"], "invalid")

    def test_zet_zaakstatus(self):
        """
        De actuele status van een zaak moet gezet worden bij het aanmaken
        van de zaak.
        """
        url = get_operation_url("status_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        statustype = StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        statustype_url = reverse(statustype)
        StatusTypeFactory.create(zaaktype=zaak.zaaktype)
        data = {
            "zaak": zaak_url,
            "statustype": f"http://testserver{statustype_url}",
            "datumStatusGezet": isodatetime(2018, 6, 6, 17, 23, 43),
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        status_ = Status.objects.get()
        self.assertEqual(status_.zaak, zaak)
        detail_url = get_operation_url("status_read", uuid=status_.uuid)
        self.assertEqual(
            response_data,
            {
                "url": f"http://testserver{detail_url}",
                "uuid": str(status_.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "statustype": f"http://testserver{statustype_url}",
                "datumStatusGezet": "2018-06-06T17:23:43Z",  # UTC
                "statustoelichting": "",
                "indicatieLaatstGezetteStatus": True,
                "gezetdoor": None,
                "zaakinformatieobjecten": [],
            },
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_zet_adres_binnenland(self):
        """
        Het adres van de melding moet in de zaak beschikbaar zijn.
        """
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": zaak_url,
            "object": OBJECT_MET_ADRES,
            "objectType": ZaakobjectTypes.adres,
            "relatieomschrijving": "Het adres waar de overlast vastgesteld werd.",
            "objectTypeOverigeDefinitie": None,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        zaakobject = ZaakObject.objects.get()
        self.assertEqual(zaakobject.zaak, zaak)
        detail_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)
        self.assertEqual(
            response_data,
            {
                "url": f"http://testserver{detail_url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "object": OBJECT_MET_ADRES,
                "objectIdentificatie": None,
                "objectType": ZaakobjectTypes.adres,
                "objectTypeOverige": "",
                "relatieomschrijving": "Het adres waar de overlast vastgesteld werd.",
                "objectTypeOverigeDefinitie": None,
                "zaakobjecttype": None,
            },
        )

    def test_create_klantcontact(self):
        url = get_operation_url("klantcontact_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": zaak_url,
            "datumtijd": isodatetime(2018, 6, 11, 13, 47, 55),
            "kanaal": "Webformulier",
            "onderwerp": "onderwerp test",
            "toelichting": "toelichting test",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        klantcontact = KlantContact.objects.get()
        self.assertIsInstance(klantcontact.identificatie, str)
        self.assertNotEqual(klantcontact.identificatie, "")
        self.assertEqual(klantcontact.zaak, zaak)
        detail_url = get_operation_url("klantcontact_read", uuid=klantcontact.uuid)
        self.assertEqual(
            response_data,
            {
                "url": f"http://testserver{detail_url}",
                "uuid": str(klantcontact.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "identificatie": klantcontact.identificatie,
                "datumtijd": "2018-06-11T13:47:55Z",
                "kanaal": "Webformulier",
                "onderwerp": "onderwerp test",
                "toelichting": "toelichting test",
            },
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_zet_stadsdeel(self):
        url = get_operation_url("zaakobject_create")
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        data = {
            "zaak": zaak_url,
            "object": STADSDEEL,
            "objectType": ZaakobjectTypes.adres,
            "relatieomschrijving": "Afgeleid gebied",
            "objectTypeOverigeDefinitie": None,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        zaakobject = ZaakObject.objects.get()
        self.assertEqual(zaakobject.zaak, zaak)
        detail_url = get_operation_url("zaakobject_read", uuid=zaakobject.uuid)
        self.assertEqual(
            response_data,
            {
                "url": f"http://testserver{detail_url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "object": STADSDEEL,
                "objectIdentificatie": None,
                "objectType": ZaakobjectTypes.adres,
                "objectTypeOverige": "",
                "relatieomschrijving": "Afgeleid gebied",
                "objectTypeOverigeDefinitie": None,
                "zaakobjecttype": None,
            },
        )

    @freeze_time("2018-01-01")
    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_zet_verantwoordelijk(self):
        url = get_operation_url("rol_create")
        betrokkene = (
            f"https://example.com/orc/api/v1/vestigingen/waternet/{uuid.uuid4().hex}"
        )
        zaak = ZaakFactory.create()
        zaak_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        roltype = RolTypeFactory.create(
            omschrijving=RolOmschrijving.behandelaar,
            omschrijving_generiek=RolOmschrijving.behandelaar,
            zaaktype=zaak.zaaktype,
        )
        rolltype_url = reverse(roltype)
        data = {
            "zaak": zaak_url,
            "betrokkene": betrokkene,
            "betrokkeneType": "vestiging",
            "roltype": f"http://testserver{rolltype_url}",
            "roltoelichting": "Baggeren van gracht",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        response_data = response.json()
        rol = Rol.objects.get()
        self.assertEqual(rol.zaak, zaak)
        self.assertEqual(rol.betrokkene, betrokkene)
        detail_url = get_operation_url("rol_read", uuid=rol.uuid)
        self.assertEqual(
            response_data,
            {
                "url": f"http://testserver{detail_url}",
                "uuid": str(rol.uuid),
                "zaak": f"http://testserver{zaak_url}",
                "betrokkene": betrokkene,
                "betrokkeneType": "vestiging",
                "afwijkendeNaamBetrokkene": "",
                "roltype": f"http://testserver{rolltype_url}",
                "omschrijving": RolOmschrijving.behandelaar,
                "omschrijvingGeneriek": RolOmschrijving.behandelaar,
                "roltoelichting": "Baggeren van gracht",
                "registratiedatum": "2018-01-01T00:00:00Z",
                "indicatieMachtiging": "",
                "betrokkeneIdentificatie": None,
                "contactpersoonRol": {
                    "emailadres": "",
                    "functie": "",
                    "telefoonnummer": "",
                    "naam": "",
                },
                "authenticatieContext": None,
                "statussen": [],
                "beginGeldigheid": None,
                "eindeGeldigheid": None,
            },
        )

    def test_identificatie_all_characters_allowed(self):
        """
        Test that there is no limitation on certain characters for the identificatie field.

        Upstream standard issue: https://github.com/VNG-Realisatie/gemma-zaken/issues/1790
        """
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        url = get_operation_url("zaak_create")
        data = {
            "identificatie": "ZK bläh",
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    @tag("gh-1271")
    def test_unexpected_request_bodies(self):
        url = get_operation_url("zaak_create")
        bad_data = ["null", "[]", "{}", ""]
        for data in bad_data:
            with self.subTest(request_body=data):
                response = self.client.post(
                    url, data, content_type="application/json", **ZAAK_WRITE_KWARGS
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CreateZaakTransactionTests(JWTAuthMixin, APITransactionTestCase):

    heeft_alle_autorisaties = True

    def setUp(self):
        self.setUpTestData()
        super().setUp()

    @tag("gh-1271")
    def test_pure_race_condition_prevented(self):
        def create_zaak1():
            try:
                # starts first, but commits last
                with transaction.atomic():
                    ZaakIdentificatie.objects.generate(
                        VERANTWOORDELIJKE_ORGANISATIE, date(2022, 12, 12)
                    )
                    time.sleep(0.1)
            finally:
                close_old_connections()

        def create_zaak2():
            try:
                with transaction.atomic():
                    ZaakIdentificatie.objects.generate(
                        VERANTWOORDELIJKE_ORGANISATIE, date(2022, 12, 12)
                    )
            finally:
                close_old_connections()

        t1 = threading.Thread(target=create_zaak1)
        t2 = threading.Thread(target=create_zaak2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        identifications = ZaakIdentificatie.objects.all()
        self.assertEqual(identifications.count(), 2)
        id1, id2 = identifications
        self.assertNotEqual(id1.identificatie, id2.identificatie)

    @tag("gh-1271")
    def test_create_with_duplicate_identifications(self):
        """
        Assert that two racing threads create different zaak identifications.

        Regression test for #1271 where transactions take too much time, causing
        multiple concurrent requests attempting to insert a zaak with the same
        generated identificatie, which violates the unique constraint.
        """
        # simulate some existing data
        zaaktype = ZaakTypeFactory.create(concept=False)
        ZaakFactory.create_batch(
            5,
            registratiedatum=date(2022, 12, 12),
            zaaktype=zaaktype,
            bronorganisatie=VERANTWOORDELIJKE_ORGANISATIE,
        )
        zaaktype_url = reverse(zaaktype)
        url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "bronorganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "registratiedatum": "2022-12-13",
            "startdatum": "2018-06-11",
        }
        next_identification = generate_unique_identification(
            Zaak(registratiedatum=date(2022, 12, 13)), "registratiedatum"
        )
        assert next_identification.startswith("ZAAK-2022-")  # sanity check

        def race_condition():
            # force a collision by executing this BEFORE the API call to create a
            # zaak.
            time.sleep(0.1)
            try:
                ZaakFactory.create(
                    registratiedatum=date(2022, 12, 13),
                    zaaktype=zaaktype,
                    bronorganisatie=VERANTWOORDELIJKE_ORGANISATIE,
                )
            finally:
                close_old_connections()

        original_perform_create = ZaakViewSet().perform_create

        def delayed_create(serializer):
            result = original_perform_create(serializer)
            time.sleep(0.3)
            return result

        def create_zaak():
            with patch(
                "openzaak.components.zaken.api.viewsets.ZaakViewSet.perform_create",
                side_effect=delayed_create,
            ):
                response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

            close_old_connections()
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        race_condition_thread = threading.Thread(target=race_condition)
        create_zaak_thread = threading.Thread(target=create_zaak)

        # start and wait for threads to finish
        create_zaak_thread.start()
        race_condition_thread.start()
        create_zaak_thread.join()
        race_condition_thread.join()

        zaken = Zaak.objects.all()
        self.assertEqual(zaken.count(), 7)  # 2 new zaken created
        self.assertEqual(zaken.filter(identificatie=next_identification).count(), 1)


@tag("performance")
class PerformanceTests(
    NotificationsConfigMixin, JWTAuthMixin, ClearCachesMixin, APITestCase
):
    """
    Tests specifically looking at performance.
    """

    scopes = [SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_ALLES_LEZEN]
    component = ComponentTypes.zrc

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)

        super().setUpTestData()

    def setUp(self):
        super().setUp()

        fetcher.cache.clear()
        self.addCleanup(fetcher.cache.clear)

    @override_settings(NOTIFICATIONS_DISABLED=False, SOLO_CACHE=None)
    @patch("notifications_api_common.viewsets.send_notification.delay")
    def test_create_zaak_local_zaaktype(self, mock_notif):
        """
        Assert that the POST /api/v1/zaken does not do too many queries.

        Breakdown of expected queries:

         1 - 4: OpenIDConnectConfig (savepoint, SELECT, INSERT and savepoint release)
             5: Consult own internal service config (SELECT FROM config_internalservice)
             6: Look up secret for auth client ID (SELECT FROM vng_api_common_jwtsecret)
           7-8: Lookup zaaktype, done by AuthRequired check of authorization fields
          9-12: Check feature flag config (PublishValidator) (savepoint, select, insert
                and savepoint release)
            13: Lookup zaaktype for permission checks
         14-17: Application/CatalogusAutorisatie/Autorisatie lookup for permission checks
            18: Begin transaction (savepoint) (from NotificationsCreateMixin)
            19: Savepoint for zaakidentificatie generation
            20: advisory lock for zaakidentificatie generation
            21: Query highest zaakidentificatie number at the  moment
            22: insert new zaakidentificatie
            23: release savepoint
            24: release savepoint (commit zaakidentificatie transaction)
            25: savepoint for zaak creation
         26-27: Lookup zaaktype for validation and cache it in serializer context
            28: Select feature flag config (PublishValidator)
            29: Lookup zaaktype (again), done by loose_fk.drf.FKOrURLField.run_validation
            30: update zaakidentificatie record (from serializer context and earlier
                generation)
            31: insert zaken_zaak record
         32-37: query related objects for etag update that may be affected (should be
                skipped, it's create of root resource!) vng_api_common.caching.signals
            38: select zaak relevantezaakrelatie (nested inline create, can't avoid this)
            39: select zaak rollen
            40: select zaak status
            41: select zaak zaakinformatieobjecten
            42: select zaak zaakobjecten
            43: select zaak kenmerken (nested inline create, can't avoid this)
            44: insert audit trail
         45-46: notifications, select created zaak (?), notifs config
            47: release savepoint (from NotificationsCreateMixin)
            48: select zaak relevantezaakrelatie (nested inline create, can't avoid this)
            49: select zaak kenmerken (nested inline create, can't avoid this)
            50: savepoint create transaction.on_commit ETag handler (start new transaction)
            51: update ETag column of zaak
            52: release savepoint (commit transaction)
        """
        # create a random zaak to get some other initial setup queries out of the way
        # (most notable figuring out the PG/postgres version)
        ZaakFactory.create()

        EXPECTED_NUM_QUERIES = 52

        zaaktype_url = reverse(self.zaaktype)
        url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "bronorganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
        }

        with self.assertNumQueries(EXPECTED_NUM_QUERIES):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mock_notif.assert_called_once()
