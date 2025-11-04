# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from datetime import datetime
from unittest import TestCase, skip
from unittest.mock import Mock, patch

from django.db.models import Model
from django.test import override_settings, tag
from django.utils import timezone

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze,
    RolOmschrijving,
    RolTypes,
    VertrouwelijkheidsAanduiding,
    ZaakobjectTypes,
)
from vng_api_common.notes.constants import NotitieStatus
from vng_api_common.tests import reverse
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.constants import ArchiefNominatieChoices
from openzaak.components.catalogi.tests.factories import (
    CatalogusFactory,
    InformatieObjectTypeFactory,
    ResultaatTypeFactory,
    RolTypeFactory,
    StatusTypeFactory,
    ZaakTypeFactory,
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.models import ZaakVerzoek
from openzaak.components.zaken.tests.test_rol import BETROKKENE
from openzaak.config.models import CloudEventConfig
from openzaak.tests.utils import JWTAuthMixin, patch_resource_validator

from ..api import cloud_events
from ..api.cloud_events import (
    ZAAK_GEMUTEERD,
    ZAAK_GEOPEND,
    ZAAK_VERWIJDEREN,
)
from ..models import (
    Resultaat,
    Rol,
    Status,
    SubStatus,
    Zaak,
    ZaakContactMoment,
    ZaakInformatieObject,
    ZaakNotitie,
    ZaakObject,
)
from .factories import (
    ResultaatFactory,
    RolFactory,
    StatusFactory,
    ZaakContactMomentFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
    ZaakNotitieFactory,
    ZaakObjectFactory,
    ZaakVerzoekFactory,
)
from .utils import ZAAK_WRITE_KWARGS


def patch_send_cloud_event():
    return patch(
        "openzaak.components.zaken.api.cloud_events.send_cloud_event.delay",
        autospec=True,
    )


class CloudEventSettingMixin(TestCase):
    CLOUD_EVENT_SOURCE = "urn:nld:oin:00000001823288444000:zakensysteem"
    CLOUD_EVENT_TIME = "2025-09-23T12:00:00Z"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._freezer = freeze_time(cls.CLOUD_EVENT_TIME)
        cls._freezer.start()

        cls._override = override_settings(ENABLE_CLOUD_EVENTS=True)
        cls._override.enable()

    def setUp(self):
        super().setUp()

        self._patcher = patch(
            "openzaak.components.zaken.api.cloud_events.CloudEventConfig.get_solo",
            return_value=CloudEventConfig(
                enabled=True,
                source=self.CLOUD_EVENT_SOURCE,
            ),
        )
        self.mock_get_solo = self._patcher.start()
        self.addCleanup(self._patcher.stop)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_freezer"):
            cls._freezer.stop()
        if hasattr(cls, "_override"):
            cls._override.disable()
        super().tearDownClass()

    def assert_cloud_event_sent(self, event_type: str, obj: Model, mock_send: Mock):
        mock_send.assert_called_once()

        args, kwargs = mock_send.call_args

        self.assertEqual(len(args), 1)
        self.assertEqual(len(kwargs), 0)

        event_payload = args[0]

        self.assertIn("id", event_payload)

        event_payload_copy = dict(event_payload)
        event_payload_copy.pop("id", None)

        expected_payload = {
            "specversion": "1.0",
            "type": event_type,
            "source": self.CLOUD_EVENT_SOURCE,
            "subject": str(obj.uuid),
            "dataref": reverse(obj),
            "datacontenttype": "application/json",
            "data": {},
            "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        self.assertEqual(event_payload_copy, expected_payload)
        self.assertIn("id", event_payload)


class ZaakCloudEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_patch_zaak_sends_zaak_gemuteerd_cloud_event(self):
        zaak = ZaakFactory.create()

        with patch_send_cloud_event() as mock_send:
            response = self.client.patch(
                reverse(zaak),
                {"toelichting": "Updated toelichting"},
                **ZAAK_WRITE_KWARGS,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, zaak, mock_send)

            args, kwargs = mock_send.call_args

            self.assertEqual(len(args), 1)
            self.assertEqual(len(kwargs), 0)

            event_payload = args[0]

            self.assertIn("id", event_payload)

            event_payload_copy = dict(event_payload)
            event_payload_copy.pop("id", None)

            expected_payload = {
                "specversion": "1.0",
                "type": ZAAK_GEMUTEERD,
                "source": "urn:nld:oin:00000001823288444000:zakensysteem",
                "subject": str(zaak.uuid),
                "dataref": reverse(zaak),
                "datacontenttype": "application/json",
                "data": {},
                "time": "2025-09-23T12:00:00Z",
            }

            self.assertEqual(event_payload_copy, expected_payload)
            self.assertIn("id", event_payload)

    def test_delete_zaak_sends_zaak_verwijderd_cloud_event(self):
        zaak = ZaakFactory.create()

        with patch_send_cloud_event() as mock_send:
            response = self.client.delete(reverse(zaak))

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assert_cloud_event_sent(ZAAK_VERWIJDEREN, zaak, mock_send)

            args, kwargs = mock_send.call_args

            self.assertEqual(len(args), 1)
            self.assertEqual(len(kwargs), 0)

            event_payload = args[0]

            event_payload_copy = dict(event_payload)
            event_payload_copy.pop("id", None)

            expected_payload = {
                "specversion": "1.0",
                "type": ZAAK_VERWIJDEREN,
                "source": "urn:nld:oin:00000001823288444000:zakensysteem",
                "subject": str(zaak.uuid),
                "dataref": reverse(zaak),
                "datacontenttype": "application/json",
                "data": {},
                "time": "2025-09-23T12:00:00Z",
            }

            self.assertEqual(event_payload_copy, expected_payload)
            self.assertIn("id", event_payload)

    def test_create_zaak_sends_zaak_gemuteerd_cloud_event(self):
        catalogus = CatalogusFactory.create()
        zaaktype = ZaakTypeFactory.create(
            uuid="4f2aa64b-eb42-491f-ba48-e27e8f66716c",
            catalogus=catalogus,
            concept=False,
        )

        with patch_send_cloud_event() as mock_send:
            zaaktype_url = reverse(zaaktype)

            response = self.client.post(
                reverse("zaak-list"),
                data={
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "productenOfDiensten": ["https://example.com/product/123"],
                },
                format="json",
                **ZAAK_WRITE_KWARGS,
            )

            zaak = Zaak.objects.get()

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, zaak, mock_send)

            args, kwargs = mock_send.call_args

            self.assertEqual(len(args), 1)
            self.assertEqual(len(kwargs), 0)

            event_payload = args[0]

            zaak = Zaak.objects.get(uuid=response.data["uuid"])

            event_payload_copy = dict(event_payload)
            event_payload_copy.pop("id", None)

            expected_payload = {
                "specversion": "1.0",
                "type": ZAAK_GEMUTEERD,
                "source": "urn:nld:oin:00000001823288444000:zakensysteem",
                "subject": str(zaak.uuid),
                "dataref": reverse(zaak),
                "datacontenttype": "application/json",
                "data": {},
                "time": "2025-09-23T12:00:00Z",
            }

            self.assertEqual(event_payload_copy, expected_payload)
            self.assertIn("id", event_payload)

    @tag("gh-2179")
    def test_patch_zaak_with_only_laatst_geopend_sends_zaak_geopend_event(self):
        zaak = ZaakFactory.create()

        with patch(
            "openzaak.components.zaken.api.cloud_events.send_cloud_event.delay",
            autospec=True,
        ) as mock_send:
            response = self.client.patch(
                reverse(zaak),
                {"laatst_geopend": "2025-01-01T12:00:00"},
                **ZAAK_WRITE_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        zaak.refresh_from_db()
        self.assertEqual(
            zaak.laatst_geopend, timezone.make_aware(datetime(2025, 1, 1, 12, 0, 0))
        )

        mock_send.assert_called_once()

        args, kwargs = mock_send.call_args

        self.assertEqual(len(args), 1)
        self.assertEqual(len(kwargs), 0)

        event_payload = args[0]

        zaak = Zaak.objects.get(uuid=response.data["uuid"])

        event_payload_copy = dict(event_payload)
        event_payload_copy.pop("id", None)

        expected_payload = {
            "specversion": "1.0",
            "type": ZAAK_GEOPEND,
            "source": "urn:nld:oin:00000001823288444000:zakensysteem",
            "subject": str(zaak.uuid),
            "dataref": reverse(zaak),
            "datacontenttype": "application/json",
            "data": {},
            "time": "2025-09-23T12:00:00Z",
        }

        self.assertEqual(event_payload_copy, expected_payload)
        self.assertIn("id", event_payload)

    def test_send_cloud_event_task_posts_expected_payload(self):
        service = ServiceFactory.create(
            api_root="http://webhook.local",
            auth_type=AuthTypes.api_key,
            header_key="Authorization",
            header_value="Token foo",
        )

        zaak = ZaakFactory.create()

        mock_config = CloudEventConfig(
            enabled=True,
            source="urn:nld:oin:00000001823288444000:zakensysteem",
            webhook_service=service,
            webhook_path="/events",
        )
        self.mock_get_solo.return_value = mock_config

        event_id = str(uuid.uuid4())
        payload = {
            "specversion": "1.0",
            "type": ZAAK_GEOPEND,
            "source": "urn:nld:oin:00000001823288444000:zakensysteem",
            "subject": str(zaak.uuid),
            "dataref": reverse(zaak),
            "datacontenttype": "application/json",
            "data": {},
            "time": "2025-09-23T12:00:00Z",
            "id": event_id,
        }

        with requests_mock.Mocker() as m:
            m.post("http://webhook.local/events")

            cloud_events.send_cloud_event(payload)

        self.assertEqual(len(m.request_history), 1)

        request = m.request_history[0]

        self.assertEqual(request.url, "http://webhook.local/events")
        self.assertEqual(request.json(), payload)
        self.assertEqual(
            request.headers["content-type"], "application/cloudevents+json"
        )
        self.assertEqual(request.headers["Authorization"], "Token foo")


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
class ResultaatCloudEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaak = ZaakFactory.create()
        cls.resultaattype = ResultaatTypeFactory.create(zaaktype=cls.zaak.zaaktype)

        cls.data = {
            "zaak": f"http://testserver{reverse(cls.zaak)}",
            "resultaattype": f"http://testserver{reverse(cls.resultaattype)}",
            "toelichting": "2025-01-01T12:00:00",
        }

    def test_resultaat_create_sends_gemuteerd_cloud_event(self):
        with patch_send_cloud_event() as mock_send:
            response = self.client.post(reverse(Resultaat), self.data)

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

    def test_resultaat_update_sends_gemuteerd_cloud_event(self):
        resultaat = ResultaatFactory.create(
            zaak=self.zaak, resultaattype=self.resultaattype
        )
        with patch_send_cloud_event() as mock_send:
            response = self.client.put(reverse(resultaat), self.data)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

            mock_send.reset_mock()

            response = self.client.patch(reverse(resultaat), self.data)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

    def test_resultaat_destroy_sends_gemuteerd_cloud_event(self):
        resultaat = ResultaatFactory.create(
            zaak=self.zaak, resultaattype=self.resultaattype
        )
        with patch_send_cloud_event() as mock_send:
            response = self.client.delete(reverse(resultaat))

            self.assertEqual(
                response.status_code, status.HTTP_204_NO_CONTENT, response.data
            )
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)


class StatusCloudEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaak = ZaakFactory.create()
        cls.statustype = StatusTypeFactory.create(zaaktype=cls.zaak.zaaktype)
        # Make sure there is a different eindstatustype
        StatusTypeFactory.create(zaaktype=cls.zaak.zaaktype)

    def test_status_create_sends_gemuteerd_cloud_event(self):
        with patch_send_cloud_event() as mock_send:
            response = self.client.post(
                reverse(Status),
                {
                    "zaak": f"http://testserver{reverse(self.zaak)}",
                    "statustype": f"http://testserver{reverse(self.statustype)}",
                    "datum_status_gezet": "2025-01-01T12:00:00",
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
class RolCloudEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaak = ZaakFactory.create()
        cls.roltype = RolTypeFactory.create(zaaktype=cls.zaak.zaaktype)

        cls.data = {
            "zaak": f"http://testserver{reverse(cls.zaak)}",
            "roltype": f"http://testserver{reverse(cls.roltype)}",
            "betrokkene": f"https://example.com/orc/api/v1/vestigingen/waternet/{uuid.uuid4().hex}",
            "betrokkeneType": RolTypes.organisatorische_eenheid,
            "roltoelichting": "test",
        }

    def test_rol_create_sends_gemuteerd_cloud_event(self):
        with patch_send_cloud_event() as mock_send:
            response = self.client.post(reverse(Rol), self.data)

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

    def test_rol_update_sends_gemuteerd_cloud_event(self):
        rol = RolFactory.create(zaak=self.zaak, roltype=self.roltype)
        with patch_send_cloud_event() as mock_send:
            response = self.client.put(reverse(rol), self.data)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

    def test_rol_destroy_sends_gemuteerd_cloud_event(self):
        rol = RolFactory.create(zaak=self.zaak, roltype=self.roltype)
        with patch_send_cloud_event() as mock_send:
            response = self.client.delete(reverse(rol))

            self.assertEqual(
                response.status_code, status.HTTP_204_NO_CONTENT, response.data
            )
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
@patch_resource_validator
@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
class ZaakContactMomentCloudEventTests(
    CloudEventSettingMixin, JWTAuthMixin, APITestCase
):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.CONTACTMOMENTEN_BASE = "https://contactmomenten.nl/api/v1/"
        cls.CONTACTMOMENT = f"{cls.CONTACTMOMENTEN_BASE}contactmomenten/1234"

        ServiceFactory.create(
            api_type=APITypes.orc,
            api_root=cls.CONTACTMOMENTEN_BASE,
            label="contactmomenten",
            auth_type=AuthTypes.zgw,
        )
        cls.zaak = ZaakFactory.create()

    def test_zaak_contanct_create_sends_gemuteerd_cloud_event(self, *mocks):
        with requests_mock.Mocker() as m:
            m.post(
                f"{self.CONTACTMOMENTEN_BASE}objectcontactmomenten",
                json={
                    "url": f"{self.CONTACTMOMENTEN_BASE}objectcontactmomenten/1",
                    "contactmoment": self.CONTACTMOMENT,
                    "object": f"http://testserver{reverse(self.zaak)}",
                    "objectType": "zaak",
                },
                status_code=201,
            )

            with patch_send_cloud_event() as mock_send:
                response = self.client.post(
                    reverse(ZaakContactMoment),
                    {"contactmoment": self.CONTACTMOMENT, "zaak": reverse(self.zaak)},
                )

                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.data
                )
                self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

    def test_zaak_contanct_destroy_sends_gemuteerd_cloud_event(self, *mocks):
        zaak_contactmoment = ZaakContactMomentFactory.create(
            zaak=self.zaak,
            _objectcontactmoment=f"{self.CONTACTMOMENTEN_BASE}objectcontactmomenten/1",
        )

        with requests_mock.Mocker() as m:
            m.delete(
                zaak_contactmoment._objectcontactmoment,
                status_code=204,
            )
            with patch_send_cloud_event() as mock_send:
                response = self.client.delete(reverse(zaak_contactmoment))

                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
                self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
class ZaakInformatieObjectCloudEventTests(
    CloudEventSettingMixin, JWTAuthMixin, APITestCase
):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaak = ZaakFactory.create()
        cls.io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        cls.zio_type = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=cls.io.informatieobjecttype, zaaktype=cls.zaak.zaaktype
        )

        cls.data = {
            "zaak": f"http://testserver{reverse(cls.zaak)}",
            "informatieobject": f"http://testserver{reverse(cls.io)}",
            "titel": "titel",
            "beschrijving": "beschrijving",
        }

    def test_zaak_informatie_object_create_sends_gemuteerd_cloud_event(self):
        with patch_send_cloud_event() as mock_send:
            response = self.client.post(reverse(ZaakInformatieObject), self.data)

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

    def test_zaak_informatie_object_update_sends_gemuteerd_cloud_event(self):
        zio = ZaakInformatieObjectFactory.create(
            zaak=self.zaak, informatieobject=self.io.canonical
        )

        with patch_send_cloud_event() as mock_send:
            response = self.client.put(reverse(zio), self.data)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

            mock_send.reset_mock()

            response = self.client.patch(reverse(zio), self.data)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

    def test_zaak_informatie_object_destroy_sends_gemuteerd_cloud_event(self):
        zio = ZaakInformatieObjectFactory.create(
            zaak=self.zaak, informatieobject=self.io.canonical
        )

        with patch_send_cloud_event() as mock_send:
            response = self.client.delete(reverse(zio))

            self.assertEqual(
                response.status_code, status.HTTP_204_NO_CONTENT, response.data
            )
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
class ZaakObjectCloudEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaak = ZaakFactory.create()
        cls.OBJECT = (
            "http://example.org/api/zaakobjecten/8768c581-2817-4fe5-933d-37af92d819dd"
        )
        cls.data = {
            "zaak": f"http://testserver{reverse(cls.zaak)}",
            "object": cls.OBJECT,
            "objectType": ZaakobjectTypes.besluit,
            "relatieomschrijving": "test",
        }

    def test_zaak_object_create_sends_gemuteerd_cloud_event(self):
        with patch_send_cloud_event() as mock_send:
            response = self.client.post(reverse(ZaakObject), self.data)

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

    def test_zaak_object_update_sends_gemuteerd_cloud_event(self):
        zaakobject = ZaakObjectFactory.create(
            zaak=self.zaak, object=self.OBJECT, object_type=ZaakobjectTypes.besluit
        )

        with patch_send_cloud_event() as mock_send:
            response = self.client.put(reverse(zaakobject), self.data)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

            mock_send.reset_mock()

            response = self.client.patch(reverse(zaakobject), self.data)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

    def test_zaak_object_destroy_sends_gemuteerd_cloud_event(self):
        zaakobject = ZaakObjectFactory.create(
            zaak=self.zaak, object=self.OBJECT, object_type=ZaakobjectTypes.besluit
        )

        with patch_send_cloud_event() as mock_send:
            response = self.client.delete(reverse(zaakobject))

            self.assertEqual(
                response.status_code, status.HTTP_204_NO_CONTENT, response.data
            )
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
@patch_resource_validator
@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
class ZaakVerzoekCloudEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.VERZOEKEN_BASE = "https://verzoeken.nl/api/v1/"
        cls.VERZOEK = f"{cls.VERZOEKEN_BASE}verzoeken/1234"

        ServiceFactory.create(
            api_type=APITypes.orc,
            api_root=cls.VERZOEKEN_BASE,
            label="verzoeken",
            auth_type=AuthTypes.zgw,
        )
        cls.zaak = ZaakFactory.create()

    def test_zaak_verzoeken_create_sends_gemuteerd_cloud_event(self, *mocks):
        with requests_mock.Mocker() as m:
            m.post(
                f"{self.VERZOEKEN_BASE}objectverzoeken",
                json={
                    "url": f"{self.VERZOEKEN_BASE}objectverzoeken/1",
                    "verzoek": self.VERZOEK,
                    "object": f"http://testserver{reverse(self.zaak)}",
                    "objectType": "zaak",
                },
                status_code=201,
            )

            with patch_send_cloud_event() as mock_send:
                response = self.client.post(
                    reverse(ZaakVerzoek),
                    {"verzoek": self.VERZOEK, "zaak": reverse(self.zaak)},
                )

                self.assertEqual(
                    response.status_code, status.HTTP_201_CREATED, response.data
                )
                self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

    def test_zaak_verzoeken_destroy_sends_gemuteerd_cloud_event(self, *mocks):
        zaak_verzoek = ZaakVerzoekFactory.create(
            zaak=self.zaak, _objectverzoek=f"{self.VERZOEKEN_BASE}objectverzoeken/1"
        )
        with requests_mock.Mocker() as m:
            m.delete(
                zaak_verzoek._objectverzoek,
                status_code=204,
            )
            with patch_send_cloud_event() as mock_send:
                response = self.client.delete(reverse(zaak_verzoek))

                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
                self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
class ZaakNotitieCloudEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaak = ZaakFactory.create()
        cls.data = {
            "onderwerp": "Test onderwerp",
            "tekst": "Test tekst",
            "aangemaaktDoor": "Test",
            "gerelateerdAan": f"http://testserver{reverse(cls.zaak)}",
        }

    def test_zaak_notitie_create_sends_gemuteerd_cloud_event(self):
        with patch_send_cloud_event() as mock_send:
            response = self.client.post(reverse(ZaakNotitie), self.data)

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

    def test_zaak_notitie_update_sends_gemuteerd_cloud_event(self):
        notitie = ZaakNotitieFactory.create(
            onderwerp="Old Value",
            status=NotitieStatus.CONCEPT,
            gerelateerd_aan=self.zaak,
        )

        with patch_send_cloud_event() as mock_send:
            response = self.client.put(reverse(notitie), self.data)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)

    def test_zaak_notitie_destroy_sends_gemuteerd_cloud_event(self):
        notitie = ZaakNotitieFactory.create(gerelateerd_aan=self.zaak)

        with patch_send_cloud_event() as mock_send:
            response = self.client.delete(reverse(notitie))

            self.assertEqual(
                response.status_code, status.HTTP_204_NO_CONTENT, response.data
            )
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
class SubStatusCloudEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaak = ZaakFactory.create()
        status = StatusFactory.create(zaak=cls.zaak)
        cls.data = {
            "zaak": f"http://testserver{reverse(cls.zaak)}",
            "status": reverse(status),
            "omschrijving": "foo",
        }

    def test_substatus_create_sends_gemuteerd_cloud_event(self):
        with patch_send_cloud_event() as mock_send:
            response = self.client.post(reverse(SubStatus), self.data)

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
class ZaakAfsluitenEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype)

        cls.statustype = StatusTypeFactory.create(zaaktype=cls.zaaktype)

        cls.resultaattype = ResultaatTypeFactory(
            zaaktype=cls.zaaktype,
            brondatum_archiefprocedure_afleidingswijze=BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
            archiefnominatie=ArchiefNominatieChoices.vernietigen,
        )
        cls.resultaattype_url = reverse(cls.resultaattype)

    def test_zaak_afsluiten_post_sends_gemuteerd_cloud_event(self):
        with patch_send_cloud_event() as mock_send:
            response = self.client.post(
                reverse("zaakafsluiten", kwargs={"uuid": self.zaak.uuid}),
                {
                    "zaak": {"toelichting": "toelichting"},
                    "resultaat": {
                        "resultaattype": f"http://testserver{reverse(self.resultaattype)}",
                        "toelichting": "Behandeld",
                    },
                    "status": {
                        "statustype": f"http://testserver{reverse(self.statustype)}",
                        "datumStatusGezet": "2023-01-01T00:00:00",
                    },
                },
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
class ZaakBijwerkenEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype)

        cls.statustype_1 = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_2 = StatusTypeFactory.create(zaaktype=cls.zaaktype)

        cls.roltype = RolTypeFactory(
            zaaktype=cls.zaaktype, omschrijving_generiek=RolOmschrijving.belanghebbende
        )

    def test_zaak_bijwerken_post_sends_gemuteerd_cloud_event(self):
        with patch_send_cloud_event() as mock_send:
            response = self.client.post(
                reverse("zaakbijwerken", kwargs={"uuid": self.zaak.uuid}),
                {
                    "zaak": {"toelichting": "toelichting"},
                    "status": {
                        "statustype": f"http://testserver{reverse(self.statustype_1)}",
                        "datumStatusGezet": "2023-01-01T00:00:00",
                    },
                    "rollen": [
                        {
                            "betrokkene": "http://www.zamora-silva.org/api/betrokkene/8768c581-2817-4fe5-933d-37af92d819dd",
                            "betrokkene_type": RolTypes.natuurlijk_persoon,
                            "roltype": f"http://testserver{reverse(self.roltype)}",
                            "roltoelichting": "abc",
                        }
                    ],
                },
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
class ZaakOpschortenEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype)

        cls.statustype_1 = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_2 = StatusTypeFactory.create(zaaktype=cls.zaaktype)

        cls.roltype = RolTypeFactory(
            zaaktype=cls.zaaktype, omschrijving_generiek=RolOmschrijving.belanghebbende
        )

    def test_zaak_opschorten_post_sends_gemuteerd_cloud_event(self):
        with patch_send_cloud_event() as mock_send:
            response = self.client.post(
                reverse("zaakopschorten", kwargs={"uuid": self.zaak.uuid}),
                {
                    "zaak": {
                        "opschorting": {"indicatie": True, "reden": "test"},
                    },
                    "status": {
                        "statustype": f"http://testserver{reverse(self.statustype_1)}",
                        "datumStatusGezet": "2023-01-01T00:00:00",
                    },
                },
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
class ZaakRegistrerenEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        cls.zaaktype = ZaakTypeFactory.create(
            concept=False, catalogus=cls.informatieobjecttype.catalogus
        )

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=cls.zaaktype, informatieobjecttype=cls.informatieobjecttype
        )

        cls.roltype = RolTypeFactory(zaaktype=cls.zaaktype)
        cls.statustype_1 = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_2 = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.informatieobject = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=cls.informatieobjecttype
        )

        cls.zaak = {
            "zaaktype": f"http://testserver{reverse(cls.zaaktype)}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
            "toelichting": "toelichting",
        }

        cls.rol = {
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(cls.roltype)}",
            "roltoelichting": "awerw",
        }

        cls.zio = {
            "informatieobject": f"http://testserver{reverse(cls.informatieobject)}",
            "titel": "string",
            "beschrijving": "string",
            "vernietigingsdatum": "2019-08-24T14:15:22Z",
        }

        cls.zaakobject = {
            "objectType": ZaakobjectTypes.overige,
            "objectTypeOverige": "test",
            "relatieomschrijving": "test",
            "objectIdentificatie": {"overigeData": {"someField": "some value"}},
        }

        cls.status = {
            "statustype": f"http://testserver{reverse(cls.statustype_1)}",
            "datumStatusGezet": "2023-01-01T00:00:00",
        }

    def test_zaak_registreren_post_sends_gemuteerd_cloud_event(self):
        with patch_send_cloud_event() as mock_send:
            response = self.client.post(
                reverse("registreerzaak-list"),
                {
                    "zaak": self.zaak,
                    "rollen": [self.rol],
                    "zaakinformatieobjecten": [self.zio],
                    "zaakobjecten": [self.zaakobject],
                    "status": self.status,
                },
            )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            self.assert_cloud_event_sent(
                ZAAK_GEMUTEERD,
                Zaak.objects.get(uuid=response.data["zaak"]["uuid"]),
                mock_send,
            )


@skip(reason="#2179 waiting for the issue to be decided for all endpoints")
class ZaakVerlengenEventTests(CloudEventSettingMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype)

        cls.statustype_1 = StatusTypeFactory.create(zaaktype=cls.zaaktype)
        cls.statustype_2 = StatusTypeFactory.create(zaaktype=cls.zaaktype)

    def test_zaak_verlengen_post_sends_gemuteerd_cloud_event(self):
        with patch_send_cloud_event() as mock_send:
            response = self.client.post(
                reverse("zaakverlengen", kwargs={"uuid": self.zaak.uuid}),
                {
                    "zaak": {
                        "verlenging": {"duur": "P5D", "reden": "test"},
                    },
                    "status": {
                        "statustype": f"http://testserver{reverse(self.statustype_1)}",
                        "datumStatusGezet": "2023-01-01T00:00:00",
                    },
                },
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assert_cloud_event_sent(ZAAK_GEMUTEERD, self.zaak, mock_send)
