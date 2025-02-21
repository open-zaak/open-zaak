# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ZaakobjectTypes
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import ZaakObjectTypeFactory
from openzaak.tests.utils import JWTAuthMixin, mock_ztc_oas_get

from ..models import ZaakObject
from .factories import ZaakFactory, ZaakObjectFactory
from .utils import (
    get_catalogus_response,
    get_zaakobjecttype_response,
    get_zaaktype_response,
)

OBJECT = "http://example.org/api/zaakobjecten/8768c581-2817-4fe5-933d-37af92d819dd"


@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
class ZaakObjectZaakobjecttypeTestCase(JWTAuthMixin, APITestCase):
    """
    tests with local zaakobject.zaakobjecttype
    """

    heeft_alle_autorisaties = True
    maxDiff = None

    def test_read_zaakobject_with_zaakobjecttype(self):
        zaakobjecttype = ZaakObjectTypeFactory.create()
        zaak = ZaakFactory.create(zaaktype=zaakobjecttype.zaaktype)
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak,
            object=OBJECT,
            object_type=ZaakobjectTypes.adres,
            zaakobjecttype=zaakobjecttype,
        )
        url = reverse(zaakobject)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{reverse(zaak)}",
                "object": OBJECT,
                "objectType": ZaakobjectTypes.adres,
                "objectTypeOverige": "",
                "relatieomschrijving": "",
                "objectTypeOverigeDefinitie": None,
                "zaakobjecttype": f"http://testserver{reverse(zaakobjecttype)}",
                "objectIdentificatie": None,
            },
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_create_zaakobject_with_zaakobjecttype(self):
        zaakobjecttype = ZaakObjectTypeFactory.create()
        zaak = ZaakFactory.create(zaaktype=zaakobjecttype.zaaktype)
        url = reverse("zaakobject-list")
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "object": OBJECT,
            "objectType": ZaakobjectTypes.adres,
            "relatieomschrijving": "test",
            "zaakobjecttype": f"http://testserver{reverse(zaakobjecttype)}",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakObject.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()

        self.assertEqual(zaakobject.zaakobjecttype, zaakobjecttype)

    def test_create_zaakobject_zaakobjecttype_from_other_catalogus_fail(self):
        zaakobjecttype = ZaakObjectTypeFactory.create()
        zaak = ZaakFactory.create()
        url = reverse("zaakobject-list")
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "object": OBJECT,
            "objectType": ZaakobjectTypes.adres,
            "relatieomschrijving": "test",
            "zaakobjecttype": f"http://testserver{reverse(zaakobjecttype)}",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(validation_error["code"], "zaaktype-mismatch")

    def test_patch_zaakobject_with_zaakobjecttype(self):
        zaakobjecttype = ZaakObjectTypeFactory.create()
        zaak = ZaakFactory.create(zaaktype=zaakobjecttype.zaaktype)
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak,
            object=OBJECT,
            object_type=ZaakobjectTypes.adres,
            zaakobjecttype=zaakobjecttype,
        )
        url = reverse(zaakobject)

        response = self.client.patch(url, {"relatieomschrijving": "new"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        zaakobject.refresh_from_db()

        self.assertEqual(zaakobject.relatieomschrijving, "new")
        self.assertEqual(zaakobject.zaakobjecttype, zaakobjecttype)

    def test_patch_zaakobject_change_zaakobjecttype_fail(self):
        zaakobjecttype = ZaakObjectTypeFactory.create()
        other_zaakobjecttype = ZaakObjectTypeFactory.create()
        zaak = ZaakFactory.create(zaaktype=zaakobjecttype.zaaktype)
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak,
            object=OBJECT,
            object_type=ZaakobjectTypes.adres,
            zaakobjecttype=other_zaakobjecttype,
        )
        url = reverse(zaakobject)

        response = self.client.patch(
            url, {"zaakobjecttype": f"http://testserver{reverse(zaakobjecttype)}"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "zaakobjecttype")
        self.assertEqual(validation_error["code"], "wijzigen-niet-toegelaten")


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakObjectExternalURLsTestCase(JWTAuthMixin, APITestCase):
    """
    tests with external zaakobject.zaakobjecttype
    """

    catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
    zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
    zaakobjecttype = "https://externe.catalogus.nl/api/v1/zaakobjecttypen/7a3e4a22-d789-4381-939b-401dbce29426"

    heeft_alle_autorisaties = True
    maxDiff = None

    def test_read_with_zaakobjecttype_external(self):
        zaakobject = ZaakObjectFactory.create(
            object=OBJECT,
            object_type=ZaakobjectTypes.adres,
            zaakobjecttype=self.zaakobjecttype,
        )
        url = reverse(zaakobject)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{url}",
                "uuid": str(zaakobject.uuid),
                "zaak": f"http://testserver{reverse(zaakobject.zaak)}",
                "object": OBJECT,
                "objectType": ZaakobjectTypes.adres,
                "objectTypeOverige": "",
                "relatieomschrijving": "",
                "objectTypeOverigeDefinitie": None,
                "zaakobjecttype": self.zaakobjecttype,
                "objectIdentificatie": None,
            },
        )

    @requests_mock.Mocker()
    def test_create_with_zaakobjecttype_external(self, m):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        url = reverse("zaakobject-list")
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "object": OBJECT,
            "objectType": ZaakobjectTypes.adres,
            "relatieomschrijving": "test",
            "zaakobjecttype": self.zaakobjecttype,
        }
        # mocks
        mock_ztc_oas_get(m)
        m.get(
            self.zaakobjecttype,
            json=get_zaakobjecttype_response(
                self.zaakobjecttype, self.zaaktype, catalogus=self.catalogus
            ),
        )
        m.get(self.zaaktype, json=get_zaaktype_response(self.catalogus, self.zaaktype))
        m.get(
            self.catalogus, json=get_catalogus_response(self.catalogus, self.zaaktype)
        )
        m.get(OBJECT, json={"url": OBJECT})

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakObject.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()

        self.assertEqual(zaakobject.zaakobjecttype, self.zaakobjecttype)

    def test_create_with_zaakobjecttype_bad_url_fail(self):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        url = reverse("zaakobject-list")
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "object": OBJECT,
            "objectType": ZaakobjectTypes.adres,
            "relatieomschrijving": "test",
            "zaakobjecttype": "abcd",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "zaakobjecttype")
        self.assertEqual(error["code"], "bad-url")

    @requests_mock.Mocker()
    def test_create_with_zaakobjecttype_invalid_schema_fail(self, m):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        url = reverse("zaakobject-list")
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "object": OBJECT,
            "objectType": ZaakobjectTypes.adres,
            "relatieomschrijving": "test",
            "zaakobjecttype": self.zaakobjecttype,
        }
        # mocks
        mock_ztc_oas_get(m)
        m.get(
            self.zaakobjecttype,
            json={"url": self.zaakobjecttype, "zaaktype": self.zaaktype},
        )
        m.get(self.zaaktype, json=get_zaaktype_response(self.catalogus, self.zaaktype))
        m.get(
            self.catalogus, json=get_catalogus_response(self.catalogus, self.zaaktype)
        )
        m.get(OBJECT, json={"url": OBJECT})

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "zaakobjecttype")
        self.assertEqual(error["code"], "invalid-resource")

    @requests_mock.Mocker()
    def test_create_with_zaakobjecttype_zaaktype_mismatch_fail(self, m):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        url = reverse("zaakobject-list")
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "object": OBJECT,
            "objectType": ZaakobjectTypes.adres,
            "relatieomschrijving": "test",
            "zaakobjecttype": self.zaakobjecttype,
        }
        # mocks
        mock_ztc_oas_get(m)
        m.get(
            self.zaakobjecttype,
            json=get_zaakobjecttype_response(
                self.zaakobjecttype, self.zaaktype, catalogus=self.catalogus
            ),
        )
        m.get(self.zaaktype, json=get_zaaktype_response(self.catalogus, self.zaaktype))
        m.get(
            self.catalogus, json=get_catalogus_response(self.catalogus, self.zaaktype)
        )
        m.get(OBJECT, json={"url": OBJECT})

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakObject.objects.count(), 1)

        zaakobject = ZaakObject.objects.get()

        self.assertEqual(zaakobject.zaakobjecttype, self.zaakobjecttype)

    def test_create_with_zaakobjecttype_unknown_service(self):
        zaak = ZaakFactory.create()
        url = reverse("zaakobject-list")
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "object": OBJECT,
            "objectType": ZaakobjectTypes.adres,
            "relatieomschrijving": "test",
            "zaakobjecttype": self.zaakobjecttype,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "zaakobjecttype")
        self.assertEqual(error["code"], "unknown-service")

    def test_patch_with_zaakobjecttype_external(self):
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak,
            object=OBJECT,
            zaakobjecttype=self.zaakobjecttype,
            relatieomschrijving="old",
        )
        url = reverse(zaakobject)

        response = self.client.patch(url, {"relatieomschrijving": "new"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        zaakobject.refresh_from_db()

        self.assertEqual(zaakobject.relatieomschrijving, "new")

    @requests_mock.Mocker()
    def test_patch_change_zaakobjecttype_fail(self, m):
        another_zot = "https://externe.catalogus.nl/api/v1/zaakobjecttypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        zaak = ZaakFactory.create(zaaktype=self.zaaktype)
        zaakobject = ZaakObjectFactory.create(
            zaak=zaak,
            object=OBJECT,
            zaakobjecttype=self.zaakobjecttype,
            relatieomschrijving="old",
        )
        url = reverse(zaakobject)
        # mocks
        mock_ztc_oas_get(m)
        m.get(
            self.zaakobjecttype,
            json=get_zaakobjecttype_response(
                self.zaakobjecttype, self.zaaktype, catalogus=self.catalogus
            ),
        )
        m.get(
            another_zot,
            json=get_zaakobjecttype_response(
                another_zot, self.zaaktype, catalogus=self.catalogus
            ),
        )

        response = self.client.patch(url, {"zaakobjecttype": another_zot})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "zaakobjecttype")
        self.assertEqual(validation_error["code"], "wijzigen-niet-toegelaten")
