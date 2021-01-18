# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import contextlib
import hashlib
import json
import os
import sys
import uuid
from datetime import date

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import serializers
from django.core.cache import caches
from django.db.models import Model
from django.utils import timezone

from djangorestframework_camel_case.util import camelize
from drc_cmis.client_builder import get_cmis_client
from drc_cmis.models import CMISConfig
from drc_cmis.utils.convert import make_absolute_uri
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.models import JWTSecret
from vng_api_common.tests import generate_jwt_auth, reverse
from zds_client.tests.mocks import MockClient
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.accounts.models import User


class JWTAuthMixin:
    """
    Configure the local auth cache.

    Creates the local auth objects for permission checks, as if you're talking
    to a real AC behind the scenes.
    """

    client_id = "testsuite"
    secret = "letmein"

    user_id = "test_user_id"
    user_representation = "Test User"

    scopes = None
    heeft_alle_autorisaties = False
    component = None
    zaaktype = None
    informatieobjecttype = None
    besluittype = None
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.zeer_geheim
    host_prefix = "http://testserver"

    @classmethod
    def check_for_instance(cls, obj) -> str:
        if isinstance(obj, Model):
            return cls.host_prefix + reverse(obj)
        return obj

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        JWTSecret.objects.get_or_create(
            identifier=cls.client_id, defaults={"secret": cls.secret}
        )

        cls.applicatie = Applicatie.objects.create(
            client_ids=[cls.client_id],
            label="for test",
            heeft_alle_autorisaties=cls.heeft_alle_autorisaties,
        )

        if cls.heeft_alle_autorisaties is False:
            zaaktype_url = cls.check_for_instance(cls.zaaktype)
            besluittype_url = cls.check_for_instance(cls.besluittype)
            informatieobjecttype_url = cls.check_for_instance(cls.informatieobjecttype)

            cls.autorisatie = Autorisatie.objects.create(
                applicatie=cls.applicatie,
                component=cls.component or ComponentTypes.zrc,
                scopes=cls.scopes or [],
                zaaktype=zaaktype_url or "",
                informatieobjecttype=informatieobjecttype_url or "",
                besluittype=besluittype_url or "",
                max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
            )

    def setUp(self):
        super().setUp()

        token = generate_jwt_auth(
            client_id=self.client_id,
            secret=self.secret,
            user_id=self.user_id,
            user_representation=self.user_representation,
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)


class ClearCachesMixin:
    def setUp(self):
        self._clear_caches()
        self.addCleanup(self._clear_caches)

    def _clear_caches(self):
        for cache in caches.all():
            cache.clear()


class AdminTestMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = User.objects.create_superuser(
            username="demo",
            email="demo@demo.com",
            password="demo",
            first_name="first",
            last_name="last",
        )

    def setUp(self) -> None:
        super().setUp()
        self.client.login(username="demo", password="demo")

    def tearDown(self) -> None:
        super().tearDown()
        self.client.logout()


no_fetch = object()


@contextlib.contextmanager
def mock_client(responses: dict):
    try:
        from django.test import override_settings
    except ImportError as exc:
        raise ImportError("You can only use this in a django context") from exc

    try:
        json_string = json.dumps(responses).encode("utf-8")
        md5 = hashlib.md5(json_string).hexdigest()
        name = f"MockClient{md5}"
        # create the class
        type(name, (MockClient,), {"responses": responses})
        dotted_path = f"zds_client.tests.mocks.{name}"
        with override_settings(ZGW_CONSUMERS_CLIENT_CLASS=dotted_path):
            yield

        # clean up
        delattr(sys.modules["zds_client.tests.mocks"], name)
    finally:
        pass


class MockSchemasMixin:
    """
    Mock fetching the schema's from Github.
    """

    mocker_attr = "adapter"

    def setUp(self):
        from openzaak.tests.utils import mock_service_oas_get

        super().setUp()

        mocker = getattr(self, self.mocker_attr)

        mock_service_oas_get(mocker, "brc", oas_url=settings.BRC_API_SPEC)
        mock_service_oas_get(mocker, "drc", oas_url=settings.DRC_API_SPEC)
        mock_service_oas_get(mocker, "zrc", oas_url=settings.ZRC_API_SPEC)
        mock_service_oas_get(mocker, "ztc", oas_url=settings.ZTC_API_SPEC)


class CMISMixin:
    def setUp(self) -> None:
        super().setUp()

        import requests_mock

        # real_http=True to let the other calls pass through and use a different mocker
        # in specific tests cases to catch those requests
        self.adapter = requests_mock.Mocker(real_http=True)
        self.adapter.start()

        self.addCleanup(self._cleanup_alfresco)

        # testserver vs. example.com
        Site.objects.clear_cache()

    def _cleanup_alfresco(self) -> None:
        # Removes the created documents from alfresco
        client = get_cmis_client()
        client.delete_cmis_folders_in_base()
        self.adapter.stop()


class OioMixin:
    base_zaak = None
    base_zaaktype = None
    base_besluit = None

    def create_zaak_besluit_services(
        self, base_besluit: str = None, base_zaak: str = None, base_zaaktype: str = None
    ):
        site = Site.objects.get_current()
        self.base_besluit = base_besluit or f"http://{site.domain}/besluiten/api/v1/"
        self.base_zaak = base_zaak or f"http://{site.domain}/zaken/api/v1/"
        self.base_zaaktype = base_zaaktype or f"http://{site.domain}/catalogi/api/v1/"

        Service.objects.create(
            api_type=APITypes.zrc,
            api_root=self.base_zaak,
            label="external zaken",
            auth_type=AuthTypes.no_auth,
        )
        Service.objects.create(
            api_type=APITypes.ztc,
            api_root=self.base_zaaktype,
            label="external zaaktypen",
            auth_type=AuthTypes.no_auth,
        )
        Service.objects.create(
            api_type=APITypes.brc,
            api_root=self.base_besluit,
            label="external besluiten",
            auth_type=AuthTypes.no_auth,
        )

    def create_besluit_without_zaak(self, **kwargs):
        from openzaak.components.besluiten.tests.factories import BesluitFactory
        from openzaak.tests.utils import mock_service_oas_get

        besluit = BesluitFactory.create(**kwargs)
        mock_service_oas_get(self.adapter, APITypes.brc, self.base_besluit)
        self.adapter.get(
            make_absolute_uri(reverse(besluit)),
            json={
                "verantwoordelijke_organisatie": "517439943",
                "identificatie": "123123",
                "besluittype": "http://testserver/besluittype/some-random-id",
                "datum": "2018-09-06",
                "toelichting": "Vergunning verleend.",
                "ingangsdatum": "2018-10-01",
                "vervaldatum": "2018-11-01",
            },
        )

        return besluit

    def create_besluit(self, **kwargs):
        from openzaak.components.besluiten.tests.factories import BesluitFactory
        from openzaak.tests.utils import mock_service_oas_get

        zaak = self.create_zaak()
        besluit = BesluitFactory.create(zaak=zaak, **kwargs)
        mock_service_oas_get(self.adapter, APITypes.brc, self.base_besluit)
        self.adapter.get(
            make_absolute_uri(reverse(besluit)),
            json={"zaak": make_absolute_uri(reverse(zaak))},
        )

        return besluit

    def create_zaak(self, **kwargs):
        from openzaak.components.zaken.tests.factories import ZaakFactory
        from openzaak.tests.utils import mock_service_oas_get

        zaak = ZaakFactory.create(**kwargs)

        mock_service_oas_get(self.adapter, APITypes.zrc, self.base_zaak)
        mock_service_oas_get(self.adapter, APITypes.ztc, self.base_zaaktype)

        if kwargs.get("zaaktype") is not None and isinstance(
            kwargs.get("zaaktype"), str
        ):
            zaaktype_url = kwargs.get("zaaktype")
            zaaktype_identificatie = zaaktype_url.split("/")[-1]
        else:
            zaaktype_url = make_absolute_uri(reverse(zaak.zaaktype))
            zaaktype_identificatie = zaak.zaaktype.identificatie

        self.adapter.get(
            make_absolute_uri(reverse(zaak)),
            json={
                "url": make_absolute_uri(reverse(zaak)),
                "identificatie": zaak.identificatie,
                "zaaktype": zaaktype_url,
            },
        )

        self.adapter.get(
            zaaktype_url,
            json={
                "url": zaaktype_url,
                "identificatie": zaaktype_identificatie,
                "omschrijving": "Melding Openbare Ruimte",
            },
        )
        return zaak


class APICMISTestCase(MockSchemasMixin, CMISMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        binding = os.getenv("CMIS_BINDING")
        if binding == "WEBSERVICE":
            config = CMISConfig.objects.get()
            config.client_url = "http://localhost:8082/alfresco/cmisws"
            config.binding = "WEBSERVICE"
            config.other_folder_path = "/DRC/"
            config.zaak_folder_path = "/ZRC/{{ zaaktype }}/{{ zaak }}"
            config.save()
        elif binding == "BROWSER":
            config = CMISConfig.objects.get()
            config.client_url = "http://localhost:8082/alfresco/api/-default-/public/cmis/versions/1.1/browser"
            config.binding = "BROWSER"
            config.other_folder_path = "/DRC/"
            config.zaak_folder_path = "/ZRC/{{ zaaktype }}/{{ zaak }}/"
            config.save()
        else:
            raise Exception("No CMIS binding specified")


def get_eio_response(url, **overrides):
    eio_type = (
        f"https://external.catalogus.nl/api/v1/informatieobjecttypen/{uuid.uuid4()}"
    )
    eio = {
        "url": url,
        "identificatie": "DOCUMENT-00001",
        "bronorganisatie": "272618196",
        "creatiedatum": date.today().isoformat(),
        "titel": "some titel",
        "auteur": "some auteur",
        "status": "",
        "formaat": "some formaat",
        "taal": "nld",
        "beginRegistratie": timezone.now().isoformat().replace("+00:00", "Z"),
        "versie": 1,
        "bestandsnaam": "",
        "inhoud": f"{url}/download?versie=1",
        "bestandsomvang": 100,
        "link": "",
        "beschrijving": "",
        "ontvangstdatum": None,
        "verzenddatum": None,
        "ondertekening": {"soort": "", "datum": None},
        "indicatieGebruiksrecht": None,
        "vertrouwelijkheidaanduiding": "openbaar",
        "integriteit": {"algoritme": "", "waarde": "", "datum": None},
        "informatieobjecttype": eio_type,
        "locked": False,
    }
    eio.update(**overrides)

    if overrides.get("_informatieobjecttype_url") is not None:
        eio["informatieobjecttype"] = overrides.get("_informatieobjecttype_url")

    return eio


def serialise_eio(eio, eio_url, **overrides):
    serialised_eio = json.loads(serializers.serialize("json", [eio,]))[0]["fields"]
    serialised_eio = get_eio_response(eio_url, **serialised_eio, **overrides)
    return camelize(serialised_eio)
