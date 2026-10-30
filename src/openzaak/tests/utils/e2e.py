# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Open Zaak maintainers
"""
End-to-end tests against a "foreign" ZGW implementation, recorded with VCR.

Every test creates the foreign resources it needs in its own cassette, so tests
don't depend on each other or on foreign state. ``docker/docker-compose.e2e.yml``
explains how to (re-)record.
"""

import os
import random
import string
import threading
from base64 import b64encode
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

from django.conf import settings
from django.db.models import Model
from django.test import override_settings, tag

import requests
import yaml
from maykin_common.vcr import VCRMixin
from rest_framework.test import APILiveServerTestCase
from vcr.config import RecordMode
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.models import JWTSecret
from vng_api_common.oas import fetcher
from vng_api_common.tests import reverse
from zgw_consumers.client import build_client
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test.factories import ServiceFactory
from zgw_consumers_oas.schema_loading import read_schema

from .auth import JWTAuthMixin
from .cache import ClearCachesMixin

FOREIGN = "http://127.0.0.1:8001/"
# the foreign system calls us back here, see docker/e2e/setup_configuration/data.yaml
E2E_HOST = "host.docker.internal"
E2E_LIVE_SERVER_PORT = 8765

RECORDING = VCRMixin.VCR_RECORD_MODE != RecordMode.NONE


@tag("e2e", "external-urls")
@override_settings(ALLOWED_HOSTS=["testserver", E2E_HOST])
class ForeignSystemTestCase(
    VCRMixin, ClearCachesMixin, JWTAuthMixin, APILiveServerTestCase
):
    """
    Our APIs with a foreign ZGW system on the other side.

    While recording, the foreign system verifies relations by calling our APIs back
    on the live server. On replay only our own requests are played back, so the
    live server can take any free port, and ``--parallel`` works.
    """

    # where the foreign system can reach us: all interfaces, or only the address
    # ``host.docker.internal`` resolves to (the docker0 gateway)
    host = os.environ.get("E2E_LIVE_SERVER_HOST", "0.0.0.0")
    port = E2E_LIVE_SERVER_PORT if RECORDING else 0
    our_host = f"{E2E_HOST}:{E2E_LIVE_SERVER_PORT}"
    heeft_alle_autorisaties = True

    def setUp(self):
        # a TransactionTestCase flushes the database after each test
        self.setUpTestData()
        super().setUp()

        # the standards' schemas, as from a warmed cache in production: the cassettes
        # then hold the foreign system's behaviour only, independent of earlier tests
        fetcher.cache.clear()
        self.addCleanup(fetcher.cache.clear)
        for standard, schema in (
            (settings.ZTC_API_STANDARD, "ztc"),
            (settings.DRC_API_STANDARD, "drc"),
            (settings.ZRC_API_STANDARD, "zrc"),
            (settings.BRC_API_STANDARD, "brc"),
        ):
            fetcher.cache[standard.oas_url] = yaml.safe_load(read_schema(schema))

        for api_type, api in ((APITypes.ztc, "catalogi"), (APITypes.drc, "documenten")):
            ServiceFactory.create(
                api_type=api_type,
                api_root=f"{FOREIGN}{api}/api/v1/",
                auth_type=AuthTypes.zgw,
                client_id="e2e-tests",
                secret="e2e-tests",
            )
        # for the foreign system to call us back
        JWTSecret.objects.create(identifier="foreign", secret="foreign")
        Applicatie.objects.create(
            client_ids=["foreign"], label="foreign", heeft_alle_autorisaties=True
        )

    def tearDown(self):
        if not RECORDING:
            # together with VCR refusing repeats: exactly the recorded requests
            self.assertTrue(self.cassette.all_played, "not all requests were made")
        super().tearDown()

    def _get_vcr_kwargs(self, **kwargs):
        test_thread = threading.current_thread()

        def ours_only(request):
            # requests from the live server answer the foreign system's callbacks,
            # which aren't replayed
            return request if threading.current_thread() is test_thread else None

        return super()._get_vcr_kwargs(**kwargs) | {"before_record_request": ours_only}

    def our_url(self, instance: Model) -> str:
        return f"http://{self.our_host}{reverse(instance)}"

    @contextmanager
    def sent_requests(self) -> Iterator[list[requests.PreparedRequest]]:
        """
        The requests this test sends, in order, both when recording and replaying.
        """
        sent: list[requests.PreparedRequest] = []
        send = requests.Session.send
        test_thread = threading.current_thread()

        def spy(session, request, **kwargs):
            if threading.current_thread() is test_thread:
                sent.append(request)
            return send(session, request, **kwargs)

        with patch.object(requests.Session, "send", spy):
            yield sent

    # the foreign resources, created over the standard APIs

    def foreign_post(self, api_type: APITypes, resource: str, data: dict) -> str:
        with build_client(Service.objects.get(api_type=api_type)) as client:
            response = client.post(resource, json=data)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["url"]

    def foreign_publish(self, url: str) -> None:
        with build_client(Service.objects.get(api_type=APITypes.ztc)) as client:
            response = client.post(f"{url}/publish")
        self.assertEqual(response.status_code, 200, response.text)

    def create_foreign_catalogus(self) -> str:
        return self.foreign_post(
            APITypes.ztc,
            "catalogussen",
            {
                "domein": "".join(random.choices(string.ascii_uppercase, k=5)),
                "rsin": "159351741",
                "contactpersoonBeheerNaam": "e2e",
            },
        )

    def create_foreign_informatieobjecttype(self, catalogus: str) -> str:
        informatieobjecttype = self.foreign_post(
            APITypes.ztc,
            "informatieobjecttypen",
            {
                "catalogus": catalogus,
                "omschrijving": "e2e",
                "vertrouwelijkheidaanduiding": "openbaar",
                "beginGeldigheid": "2026-01-01",
                "informatieobjectcategorie": "e2e",
            },
        )
        self.foreign_publish(informatieobjecttype)
        return informatieobjecttype

    def create_foreign_zaaktype(self, catalogus: str, informatieobjecttype: str) -> str:
        zaaktype = self.foreign_post(
            APITypes.ztc,
            "zaaktypen",
            {
                "catalogus": catalogus,
                "identificatie": "e2e",
                "omschrijving": "e2e",
                "doel": "e2e",
                "aanleiding": "e2e",
                "indicatieInternOfExtern": "extern",
                "handelingInitiator": "indienen",
                "onderwerp": "e2e",
                "handelingBehandelaar": "uitvoeren",
                "doorlooptijd": "P30D",
                "opschortingEnAanhoudingMogelijk": False,
                "verlengingMogelijk": False,
                "publicatieIndicatie": False,
                "productenOfDiensten": [],
                "vertrouwelijkheidaanduiding": "openbaar",
                "referentieproces": {"naam": "e2e"},
                "gerelateerdeZaaktypen": [],
                "besluittypen": [],
                "verantwoordelijke": "159351741",
                "beginGeldigheid": "2026-01-01",
                "versiedatum": "2026-01-01",
            },
        )
        self.foreign_post(
            APITypes.ztc,
            "zaaktype-informatieobjecttypen",
            {
                "zaaktype": zaaktype,
                "informatieobjecttype": informatieobjecttype,
                "volgnummer": 1,
                "richting": "inkomend",
            },
        )
        return zaaktype

    def create_foreign_besluittype(
        self, catalogus: str, informatieobjecttype: str
    ) -> str:
        besluittype = self.foreign_post(
            APITypes.ztc,
            "besluittypen",
            {
                "catalogus": catalogus,
                "omschrijving": "e2e",
                "publicatieIndicatie": False,
                "informatieobjecttypen": [informatieobjecttype],
                "beginGeldigheid": "2026-01-01",
            },
        )
        self.foreign_publish(besluittype)
        return besluittype

    def create_foreign_document(self, informatieobjecttype: str) -> str:
        return self.foreign_post(
            APITypes.drc,
            "enkelvoudiginformatieobjecten",
            {
                "bronorganisatie": "159351741",
                "creatiedatum": "2026-01-01",
                "titel": "e2e",
                "auteur": "e2e",
                "taal": "nld",
                "inhoud": b64encode(b"e2e").decode(),
                "bestandsnaam": "e2e.txt",
                "informatieobjecttype": informatieobjecttype,
            },
        )
