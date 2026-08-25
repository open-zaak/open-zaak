# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ZaakobjectTypes
from vng_api_common.tests import get_validation_errors

from openzaak.components.catalogi.tests.factories import ZaakObjectTypeFactory
from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.urls import reverse

from ..models import ZaakObject
from .factories import ZaakFactory, ZaakObjectFactory

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
        url = reverse("zaken:zaakobject-list")
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
        url = reverse("zaken:zaakobject-list")
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
