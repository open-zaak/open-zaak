# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import uuid

from django.conf import settings
from django.contrib.sites.models import Site
from django.test import override_settings, tag

from drc_cmis.models import CMISConfig, UrlMapping
from drc_cmis.utils.convert import make_absolute_uri
from furl import furl
from rest_framework import status
from vng_api_common.constants import ObjectTypes
from vng_api_common.tests import (
    JWTAuthMixin,
    get_validation_errors,
    reverse,
    reverse_lazy,
)
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import mock_service_oas_get

from openzaak.components.besluiten.tests.factories import BesluitInformatieObjectFactory
from openzaak.components.besluiten.tests.utils import (
    get_besluit_response,
    get_besluitinformatieobject_response,
)
from openzaak.components.zaken.tests.factories import (
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from openzaak.components.zaken.tests.utils import (
    get_zaak_response,
    get_zaakinformatieobject_response,
    get_zaaktype_response,
)
from openzaak.tests.utils import APICMISTestCase

from ..models import ObjectInformatieObject
from .factories import EnkelvoudigInformatieObjectFactory


@tag("oio", "cmis")
@override_settings(CMIS_ENABLED=True, ALLOWED_HOSTS=["testserver", "example.com"])
class ObjectInformatieObjectTests(JWTAuthMixin, APICMISTestCase):
    heeft_alle_autorisaties = True
    list_url = reverse_lazy("objectinformatieobject-list")

    def test_retrieve_multiple_oios(self):
        zaak = ZaakFactory.create()

        # This creates 2 OIOs
        eio_1 = EnkelvoudigInformatieObjectFactory.create()
        eio_1_path = reverse(eio_1)
        eio_1_url = f"http://testserver{eio_1_path}"
        # relate the two
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=eio_1_url)

        eio_2 = EnkelvoudigInformatieObjectFactory.create()
        eio_2_path = reverse(eio_2)
        eio_2_url = f"http://testserver{eio_2_path}"
        # relate the two
        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=eio_2_url)

        # Retrieve oios from API
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 2)
        self.assertTrue(
            eio_1_url == response.data[0]["informatieobject"]
            or eio_1_url == response.data[1]["informatieobject"]
        )
        self.assertTrue(
            eio_2_url == response.data[0]["informatieobject"]
            or eio_2_url == response.data[1]["informatieobject"]
        )

    def test_create_with_objecttype_zaak(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"
        # relate the two
        zio = ZaakInformatieObjectFactory.create(informatieobject=eio_url)

        # get OIO created via signals
        ObjectInformatieObject.objects.get()

        zaak_url = reverse(zio.zaak)

        response = self.client.post(
            self.list_url,
            {
                "object": f"http://testserver{zaak_url}",
                "informatieobject": eio_url,
                "objectType": "zaak",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unique")

    def test_create_with_objecttype_besluit(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"
        bio = BesluitInformatieObjectFactory.create(informatieobject=eio_url)

        # get OIO created via signals
        ObjectInformatieObject.objects.get()

        besluit_url = reverse(bio.besluit)

        response = self.client.post(
            self.list_url,
            {
                "object": f"http://testserver{besluit_url}",
                "informatieobject": f"http://testserver{eio_path}",
                "objectType": "besluit",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unique")

    def test_create_with_objecttype_other_fail(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"
        # relate the two
        bio = BesluitInformatieObjectFactory.create(informatieobject=eio_url)

        besluit_url = reverse(bio.besluit)

        response = self.client.post(
            self.list_url,
            {
                "object": f"http://testserver{besluit_url}",
                "informatieobject": eio_url,
                "objectType": "other",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "objectType")
        self.assertEqual(error["code"], "invalid_choice")

    def test_read_with_objecttype_zaak(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"
        # relate the two
        zio = ZaakInformatieObjectFactory.create(informatieobject=eio_url)

        # get OIO created via signals
        oio = ObjectInformatieObject.objects.get()

        oio_url = reverse("objectinformatieobject-detail", kwargs={"uuid": oio.uuid})
        zaak_url = reverse(zio.zaak)

        response = self.client.get(oio_url)

        expeceted_response_data = {
            "url": f"http://testserver{oio_url}",
            "object": make_absolute_uri(zaak_url),
            "informatieobject": eio_url,
            "object_type": "zaak",
        }

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data, expeceted_response_data)

    def test_read_with_objecttype_besluit(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"
        # relate the two
        bio = BesluitInformatieObjectFactory.create(informatieobject=eio_url)

        # get OIO created via signals
        oio = ObjectInformatieObject.objects.get()

        oio_url = reverse("objectinformatieobject-detail", kwargs={"uuid": oio.uuid})
        besluit_url = reverse(bio.besluit)

        response = self.client.get(oio_url)

        expeceted_response_data = {
            "url": f"http://testserver{oio_url}",
            "object": make_absolute_uri(besluit_url),
            "informatieobject": eio_url,
            "object_type": "besluit",
        }

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data, expeceted_response_data)

    def test_post_object_without_created_relations(self):
        """
        Test the (informatieobject, object) unique together validation.

        This is expected to fail, since there is no actual creation in database.
        It will however become relevant again when we're handling remote
        references.
        """
        zaak = ZaakFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        zaak_url = reverse(zaak)
        eio_url = reverse(eio)

        content = {
            "informatieobject": f"http://testserver{eio_url}",
            "object": f"http://testserver{zaak_url}",
            "objectType": ObjectTypes.zaak,
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "inconsistent-relation")

    def test_filter_eio(self):
        eio_1 = EnkelvoudigInformatieObjectFactory.create()
        eio_2 = EnkelvoudigInformatieObjectFactory.create()
        eio_detail_url = f"http://example.com{reverse(eio_1)}"

        BesluitInformatieObjectFactory.create(informatieobject=eio_detail_url)
        ZaakInformatieObjectFactory.create(
            informatieobject=f"http://example.com{reverse(eio_2)}"
        )  # may not show up

        response = self.client.get(self.list_url, {"informatieobject": eio_detail_url},)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["informatieobject"], eio_detail_url)

    def test_filter_zaak(self):
        # Needed because the zaak URL is used as a query parameter,
        # and using "testserver" as domain name gives an invalid URL.
        site = Site.objects.get_current()
        site.domain = "example.com"
        site.save()

        eio_1 = EnkelvoudigInformatieObjectFactory.create()
        eio_detail_url = f"http://example.com{reverse(eio_1)}"

        zio = ZaakInformatieObjectFactory.create(informatieobject=eio_detail_url)
        ZaakInformatieObjectFactory.create(
            informatieobject=eio_detail_url
        )  # may not show up

        zaak_url = reverse(zio.zaak)

        response = self.client.get(
            self.list_url, {"object": f"http://example.com{zaak_url}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["informatieobject"], eio_detail_url)

    def test_filter_besluit(self):
        # Needed because the besluit URL is used as a query parameter,
        # and using "testserver" as domain name gives an invalid URL.
        site = Site.objects.get_current()
        site.domain = "example.com"
        site.save()

        eio_1 = EnkelvoudigInformatieObjectFactory.create()
        eio_detail_url = f"http://example.com{reverse(eio_1)}"

        bio = BesluitInformatieObjectFactory.create(informatieobject=eio_detail_url)
        BesluitInformatieObjectFactory.create(
            informatieobject=eio_detail_url
        )  # may not show up

        besluit_url = reverse(bio.besluit)

        response = self.client.get(
            self.list_url, {"object": f"http://example.com{besluit_url}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["informatieobject"], eio_detail_url)

    def test_validate_unknown_query_params(self):
        url = reverse(ObjectInformatieObject)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class ObjectInformatieObjectDestroyTests(JWTAuthMixin, APICMISTestCase):
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()
        super().setUpTestData()

    def test_destroy_oio_remote_gone(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"

        # relate the two
        zio = ZaakInformatieObjectFactory.create(informatieobject=eio_url)

        oio = ObjectInformatieObject.objects.get()
        url = reverse(oio)
        zio.delete()

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_destroy_oio_remote_still_present(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"

        # relate the two
        BesluitInformatieObjectFactory.create(informatieobject=eio_url)

        oio = ObjectInformatieObject.objects.get()
        url = reverse(oio)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "remote-relation-exists")


@tag("external-urls", "cmis")
@override_settings(ALLOWED_HOSTS=["testserver"], CMIS_ENABLED=True)
class OIOCreateExternalURLsTests(JWTAuthMixin, APICMISTestCase):
    heeft_alle_autorisaties = True
    list_url = reverse_lazy(ObjectInformatieObject)

    besluit = (
        "https://extern.brc.nl/api/v1/besluiten/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
    )
    besluittype = "https://externe.catalogus.nl/api/v1/besluittypen/b71f72ef-198d-44d8-af64-ae1932df830a"
    zaak = "https://extern.zrc.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
    zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
    catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/5c4c492b-3548-4258-b17f-0e2e31dcfe25"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Mocking the calls for the CMIS adapter
        Service.objects.create(
            api_type=APITypes.zrc,
            api_root="https://externe.catalogus.nl/api/v1/",
            label="external zaken",
            auth_type=AuthTypes.no_auth,
        )

        cls.zrc_service = Service.objects.create(
            label="Remote Zaken API",
            api_type=APITypes.zrc,
            api_root="https://extern.zrc.nl/api/v1/",
            auth_type=AuthTypes.zgw,
            client_id="test",
            secret="test",
        )
        cls.brc_service = Service.objects.create(
            label="Remote Besluiten API",
            api_type=APITypes.brc,
            api_root="https://extern.brc.nl/api/v1/",
            auth_type=AuthTypes.zgw,
            client_id="test",
            secret="test",
        )

        config = CMISConfig.get_solo()

        if settings.CMIS_URL_MAPPING_ENABLED:
            UrlMapping.objects.create(
                long_pattern="https://externe.catalogus.nl",
                short_pattern="https://xcat.nl",
                config=config,
            )
            UrlMapping.objects.create(
                long_pattern="https://extern.zrc.nl",
                short_pattern="https://xzrc.nl",
                config=config,
            )
            UrlMapping.objects.create(
                long_pattern="https://extern.brc.nl",
                short_pattern="https://xbrc.nl",
                config=config,
            )

    def setUp(self):
        super().setUp()

        mock_service_oas_get(
            self.adapter, "https://extern.zrc.nl/api/v1/", APITypes.zrc
        )
        mock_service_oas_get(
            self.adapter, "https://externe.catalogus.nl/api/v1/", APITypes.ztc
        )
        mock_service_oas_get(
            self.adapter, "https://extern.brc.nl/api/v1/", APITypes.brc
        )

    def test_create_external_zaak(self):
        self.adapter.get(self.zaak, json=get_zaak_response(self.zaak, self.zaaktype))
        self.adapter.get(
            self.zaaktype, json=get_zaak_response(self.catalogus, self.zaaktype)
        )

        # The test
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"

        zio_url = furl(self.zrc_service.api_root) / "zaakinformatieobjecten"
        zio_url.set({"informatieobject": eio_url, "zaak": self.zaak})

        # Remote relation exists
        self.adapter.get(
            zio_url.url, json=[get_zaakinformatieobject_response(eio_url, self.zaak)]
        )
        response = self.client.post(
            self.list_url,
            {"object": self.zaak, "informatieobject": eio_url, "objectType": "zaak",},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        oio = ObjectInformatieObject.objects.get()
        self.assertEqual(oio.get_informatieobject_url(), eio_url)

        self.assertEqual(oio.object, self.zaak)

    def test_create_external_zaak_inconsistent_relation(self):
        """
        Regression test for https://github.com/open-zaak/open-zaak/issues/1227
        """
        self.adapter.get(self.zaak, json=get_zaak_response(self.zaak, self.zaaktype))
        self.adapter.get(
            self.zaaktype, json=get_zaak_response(self.catalogus, self.zaaktype)
        )

        # The test
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"

        zio_url = furl(self.zrc_service.api_root) / "zaakinformatieobjecten"
        zio_url.set({"informatieobject": eio_url, "zaak": self.zaak})

        # Remote relation does not exist
        self.adapter.get(zio_url.url, json=[])
        response = self.client.post(
            self.list_url,
            {"object": self.zaak, "informatieobject": eio_url, "objectType": "zaak",},
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "inconsistent-relation")

    def test_create_external_besluit(self):
        self.adapter.get(
            self.besluit,
            json=get_besluit_response(self.besluit, self.besluittype, self.zaak),
        )
        self.adapter.get(self.zaak, json=get_zaak_response(self.zaak, self.zaaktype))
        self.adapter.get(
            self.zaaktype, json=get_zaak_response(self.catalogus, self.zaaktype)
        )

        # The test
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"

        bio_url = furl(self.brc_service.api_root) / "besluitinformatieobjecten"
        bio_url.set({"informatieobject": eio_url, "besluit": self.besluit})

        # Remote relation exists
        self.adapter.get(
            bio_url.url,
            json=[get_besluitinformatieobject_response(eio_url, self.besluit)],
        )

        response = self.client.post(
            self.list_url,
            {
                "object": self.besluit,
                "informatieobject": eio_url,
                "objectType": "besluit",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        oio = ObjectInformatieObject.objects.get()

        self.assertEqual(oio.get_informatieobject_url(), eio_url)
        self.assertEqual(oio.object, self.besluit)

    def test_create_external_besluit_inconsistent_relation(self):
        """
        Regression test for https://github.com/open-zaak/open-zaak/issues/1227
        """
        self.adapter.get(
            self.besluit,
            json=get_besluit_response(self.besluit, self.besluittype, self.zaak),
        )
        self.adapter.get(self.zaak, json=get_zaak_response(self.zaak, self.zaaktype))
        self.adapter.get(
            self.zaaktype, json=get_zaak_response(self.catalogus, self.zaaktype)
        )

        # The test
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        eio_url = f"http://testserver{eio_path}"

        bio_url = furl(self.brc_service.api_root) / "besluitinformatieobjecten"
        bio_url.set({"informatieobject": eio_url, "besluit": self.besluit})

        # Remote relation exists
        self.adapter.get(bio_url.url, json=[])

        response = self.client.post(
            self.list_url,
            {
                "object": self.besluit,
                "informatieobject": eio_url,
                "objectType": "besluit",
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "inconsistent-relation")

    def test_create_external_zaak_fail_invalid_schema(self):
        zaak = "https://extern.zrc.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"

        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = reverse(eio)

        self.adapter.register_uri(
            "GET",
            zaak,
            json={
                "url": zaak,
                "uuid": "d781cd1b-f100-4051-9543-153b93299da4",
                "identificatie": "ZAAK-2019-0000000001",
                "zaaktype": zaaktype,
            },
        )

        response = self.client.post(
            self.list_url,
            {
                "object": zaak,
                "informatieobject": f"http://testserver{eio_url}",
                "objectType": "zaak",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "object")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_besluit_fail_invalid_schema(self):
        besluit = "https://extern.brc.nl/api/v1/besluiten/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        besluittype = "https://externe.catalogus.nl/api/v1/besluittypen/b71f72ef-198d-44d8-af64-ae1932df830a"

        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = reverse(eio)

        self.adapter.register_uri(
            "GET",
            besluit,
            json={
                "url": besluit,
                "identificatie": "BESLUIT-2019-0000000001",
                "besluittype": besluittype,
            },
        )

        response = self.client.post(
            self.list_url,
            {
                "object": besluit,
                "informatieobject": f"http://testserver{eio_url}",
                "objectType": "besluit",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "object")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_fail_not_unique(self):
        self.adapter.get(
            self.besluit,
            json=get_besluit_response(self.besluit, self.besluittype, self.zaak),
        )
        self.adapter.get(self.zaak, json=get_zaak_response(self.zaak, self.zaaktype))
        self.adapter.get(
            self.zaaktype, json=get_zaak_response(self.catalogus, self.zaaktype)
        )

        # The test
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"

        ObjectInformatieObject.objects.create(
            informatieobject=eio_url, besluit=self.besluit, object_type="besluit"
        )

        response = self.client.post(
            self.list_url,
            {
                "object": self.besluit,
                "informatieobject": eio_url,
                "objectType": "besluit",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unique")

    def test_read_external_zaak(self):
        self.adapter.get(self.zaak, json=get_zaak_response(self.zaak, self.zaaktype))
        self.adapter.get(
            self.zaaktype, json=get_zaak_response(self.catalogus, self.zaaktype)
        )

        eio = EnkelvoudigInformatieObjectFactory.create()
        oio = ObjectInformatieObject.objects.create(
            informatieobject=f"http://testserver{reverse(eio)}",
            zaak=self.zaak,
            object_type="zaak",
        )

        url = reverse(oio)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["object"], self.zaak)
        self.assertEqual(data["informatieobject"], f"http://testserver{reverse(eio)}")

    def test_read_external_besluit(self):
        self.adapter.get(
            self.besluit,
            json=get_besluit_response(self.besluit, self.besluittype, self.zaak),
        )
        self.adapter.get(self.zaak, json=get_zaak_response(self.zaak, self.zaaktype))
        self.adapter.get(
            self.zaaktype, json=get_zaak_response(self.catalogus, self.zaaktype)
        )

        # The test
        eio = EnkelvoudigInformatieObjectFactory.create()
        oio = ObjectInformatieObject.objects.create(
            informatieobject=f"http://testserver{reverse(eio)}",
            besluit=self.besluit,
            object_type="besluit",
        )

        url = reverse(oio)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["object"], self.besluit)
        self.assertEqual(data["informatieobject"], f"http://testserver{reverse(eio)}")

    def test_list_filter_by_external_zaak(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        zaak1 = (
            "https://extern.zrc.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        )
        zaak2 = (
            "https://extern.zrc.nl/api/v1/zaken/b923543f-97aa-4a55-8c20-889b5906cf75"
        )
        zaaktype1 = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaaktype2 = "https://externe.catalogus.nl/api/v1/zaaktypen/5c4c492b-3548-4258-b17f-0e2e31dcfe25"
        catalogus1 = "https://externe.catalogus.nl/api/v1/catalogussen/5c4c492b-3548-4258-b17f-0e2e31dcfe25"
        catalogus2 = "https://externe.catalogus.nl/api/v1/catalogussen/a8e03e86-152d-4e8c-83fc-047645cfc585"

        self.adapter.get(zaak1, json=get_zaak_response(zaak1, zaaktype1))
        self.adapter.get(zaaktype1, json=get_zaak_response(catalogus1, zaaktype1))
        self.adapter.get(zaak2, json=get_zaak_response(zaak2, zaaktype2))
        self.adapter.get(zaaktype2, json=get_zaak_response(catalogus2, zaaktype2))

        ObjectInformatieObject.objects.create(
            informatieobject=f"http://testserver{reverse(eio)}",
            zaak=zaak1,
            object_type="zaak",
        )
        ObjectInformatieObject.objects.create(
            informatieobject=f"http://testserver{reverse(eio)}",
            zaak=zaak2,
            object_type="zaak",
        )

        url = reverse(ObjectInformatieObject)

        response = self.client.get(url, {"object": zaak2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["object"], zaak2)

    def test_list_filter_by_external_besluit(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        # Needed for the CMIS adapter
        zaak1 = (
            "https://extern.zrc.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        )
        zaak2 = (
            "https://extern.zrc.nl/api/v1/zaken/b923543f-97aa-4a55-8c20-889b5906cf75"
        )
        zaaktype1 = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaaktype2 = "https://externe.catalogus.nl/api/v1/zaaktypen/5c4c492b-3548-4258-b17f-0e2e31dcfe25"
        catalogus1 = "https://externe.catalogus.nl/api/v1/catalogussen/5c4c492b-3548-4258-b17f-0e2e31dcfe25"
        catalogus2 = "https://externe.catalogus.nl/api/v1/catalogussen/a8e03e86-152d-4e8c-83fc-047645cfc585"
        besluit1 = "https://extern.brc.nl/api/v1/besluiten/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        besluit2 = "https://extern.brc.nl/api/v1/besluiten/b923543f-97aa-4a55-8c20-889b5906cf75"
        besluittype1 = "https://externe.catalogus.nl/api/v1/besluittypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        besluittype2 = "https://externe.catalogus.nl/api/v1/besluittypen/3665b9be-6ac5-4075-8736-d79598e5325c"

        self.adapter.get(zaak1, json=get_zaak_response(zaak1, zaaktype1))
        self.adapter.get(zaaktype1, json=get_zaak_response(catalogus1, zaaktype1))
        self.adapter.get(zaak2, json=get_zaak_response(zaak2, zaaktype2))
        self.adapter.get(zaaktype2, json=get_zaak_response(catalogus2, zaaktype2))
        self.adapter.get(
            besluit1, json=get_besluit_response(besluit1, besluittype1, zaak1)
        )
        self.adapter.get(
            besluit2, json=get_besluit_response(besluit2, besluittype2, zaak2)
        )

        ObjectInformatieObject.objects.create(
            informatieobject=f"http://testserver{reverse(eio)}",
            besluit=besluit1,
            object_type="besluit",
        )
        ObjectInformatieObject.objects.create(
            informatieobject=f"http://testserver{reverse(eio)}",
            besluit=besluit2,
            object_type="besluit",
        )

        url = reverse(ObjectInformatieObject)

        response = self.client.get(url, {"object": besluit2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["object"], besluit2)

    def test_destroy_oio_with_external_zaak(self):
        self.adapter.get(self.zaak, json=get_zaak_response(self.zaak, self.zaaktype))
        self.adapter.get(
            self.zaaktype, json=get_zaak_response(self.catalogus, self.zaaktype)
        )

        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        oio = ObjectInformatieObject.objects.create(
            informatieobject=eio_url, zaak=self.zaak, object_type="zaak",
        )
        url = reverse(oio)

        self.adapter.get(
            f"https://extern.zrc.nl/api/v1/zaakinformatieobjecten?zaak={self.zaak}&informatieobject={eio_url}",
            json=[],
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ObjectInformatieObject.objects.count(), 0)

    def test_destroy_oio_with_external_besluit(self):
        self.adapter.get(
            self.besluit,
            json=get_besluit_response(self.besluit, self.besluittype, self.zaak),
        )
        self.adapter.get(self.zaak, json=get_zaak_response(self.zaak, self.zaaktype))
        self.adapter.get(
            self.zaaktype, json=get_zaak_response(self.catalogus, self.zaaktype)
        )

        self.adapter.get(
            self.besluit, json=get_besluit_response(self.besluit, self.besluittype),
        )

        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        oio = ObjectInformatieObject.objects.create(
            informatieobject=f"http://testserver{reverse(eio)}",
            besluit=self.besluit,
            object_type="besluit",
        )
        url = reverse(oio)

        self.adapter.get(
            "https://extern.brc.nl/api/v1/besluitinformatieobjecten"
            f"?besluit={self.besluit}&informatieobject={eio_url}",
            json=[],
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ObjectInformatieObject.objects.count(), 0)

    def test_destroy_oio_remote_still_present(self):
        zaak = "https://extern.zrc.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://extern.zrc.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        # set up mocks
        self.adapter.get(zaak, json=get_zaak_response(zaak, zaaktype))
        self.adapter.get(zaaktype, json=get_zaaktype_response(self.catalogus, zaaktype))
        self.adapter.get(
            f"https://extern.zrc.nl/api/v1/zaakinformatieobjecten?zaak={zaak}&informatieobject={eio_url}",
            json=[
                {
                    "url": f"https://extern.zrc.nl/api/v1/zaakinformatieobjecten/{uuid.uuid4()}",
                    "informatieobject": eio_url,
                    "zaak": zaak,
                    "aardRelatieWeergave": "not relevant",
                }
            ],
        )
        oio = ObjectInformatieObject.objects.create(
            informatieobject=eio_url, zaak=zaak, object_type="zaak",
        )
        url = reverse(oio)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "remote-relation-exists")
        self.assertTrue(ObjectInformatieObject.objects.exists())
