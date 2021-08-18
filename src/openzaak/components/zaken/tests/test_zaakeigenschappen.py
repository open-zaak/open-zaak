# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2021 Dimpact

from unittest.mock import patch

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, reverse

from ..api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
)
from ..models import ZaakEigenschap
from .factories import ZaakEigenschapFactory, ZaakFactory

ZTC_ROOT = "https://example.com/ztc/api/v1"
CATALOGUS = f"{ZTC_ROOT}/catalogus/878a3318-5950-4642-8715-189745f91b04"
ZAAKTYPE = f"{CATALOGUS}/zaaktypen/283ffaf5-8470-457b-8064-90e5728f413f"
EIGENSCHAP = f"{ZTC_ROOT}/eigenschappen/f420c3e0-8345-44d9-a981-0f424538b9e9"
EIGENSCHAP2 = f"{ZTC_ROOT}/eigenschappen/0ab8cc90-dfeb-4cd0-9dab-821104c90741"

RESPONSES = {
    ZAAKTYPE: {"url": ZAAKTYPE},
    EIGENSCHAP: {"url": EIGENSCHAP, "zaaktype": ZAAKTYPE, "naam": "foo"},
    EIGENSCHAP2: {"url": EIGENSCHAP2, "zaaktype": ZAAKTYPE, "naam": "bar"},
}


class ZaakEigenschappenTest(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_ALLES_LEZEN]
    zaaktype = ZAAKTYPE

    def setUp(self):
        super().setUp()

        mock_fetcher = patch("openzaak.utils.validators.fetcher")
        mock_fetcher.start()
        self.addCleanup(mock_fetcher.stop)

        mock_has_shape = patch(
            "vng_api_common.validators.obj_has_shape", return_value=True
        )
        mock_has_shape.start()
        self.addCleanup(mock_has_shape.stop)

        def _fetch_obj(url: str, do_underscoreize=True):
            return RESPONSES[url]

        mock_fetch_object = patch(
            "openzaak.loaders.AuthorizedRequestsLoader.fetch_object",
            side_effect=_fetch_obj,
        )
        mock_fetch_object.start()
        self.addCleanup(mock_fetch_object.stop)

        mock_fetch_schema = patch(
            "zds_client.client.schema_fetcher.fetch", return_value={"paths": {},},
        )
        mock_fetch_schema.start()
        self.addCleanup(mock_fetch_schema.stop)

        m = requests_mock.Mocker()
        m.start()
        m.get("https://example.com", status_code=200)
        m.get(EIGENSCHAP, json=RESPONSES[EIGENSCHAP])
        m.get(EIGENSCHAP2, json=RESPONSES[EIGENSCHAP2])
        m.get(ZAAKTYPE, json=RESPONSES[ZAAKTYPE])
        self.addCleanup(m.stop)

    def test_zaak_eigenschappen_update(self):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaakeigenschap = ZaakEigenschapFactory.create(
            zaak=zaak, eigenschap=EIGENSCHAP, waarde="This is a value"
        )

        zaakeigenschap_url = reverse(
            "zaakeigenschap-detail",
            kwargs={"version": 1, "zaak_uuid": zaak.uuid, "uuid": zaakeigenschap.uuid},
        )
        zaak_url = reverse("zaak-detail", kwargs={"version": 1, "uuid": zaak.uuid},)

        zaakeigenschap_data = {
            "zaak": f"http://example.com{zaak_url}",
            "eigenschap": EIGENSCHAP,
            "waarde": "This is a changed value",
        }

        response = self.client.put(zaakeigenschap_url, data=zaakeigenschap_data)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        zaakeigenschap.refresh_from_db()

        self.assertEqual("This is a changed value", zaakeigenschap.waarde)

    def test_zaak_eigenschappen_partial_update(self):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaakeigenschap = ZaakEigenschapFactory.create(
            zaak=zaak, eigenschap=EIGENSCHAP, waarde="This is a value"
        )

        zaakeigenschap_url = reverse(
            "zaakeigenschap-detail",
            kwargs={"version": 1, "zaak_uuid": zaak.uuid, "uuid": zaakeigenschap.uuid},
        )
        zaak_url = reverse("zaak-detail", kwargs={"version": 1, "uuid": zaak.uuid},)

        zaakeigenschap_data = {
            "zaak": f"http://example.com{zaak_url}",
            "eigenschap": EIGENSCHAP,
            "waarde": "This is a changed value",
        }

        response = self.client.patch(zaakeigenschap_url, data=zaakeigenschap_data)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        zaakeigenschap.refresh_from_db()

        self.assertEqual("This is a changed value", zaakeigenschap.waarde)

    def test_cannot_change_eigenschap(self):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaakeigenschap = ZaakEigenschapFactory.create(
            zaak=zaak, eigenschap=EIGENSCHAP, waarde="This is a value"
        )

        zaakeigenschap_url = reverse(
            "zaakeigenschap-detail",
            kwargs={"version": 1, "zaak_uuid": zaak.uuid, "uuid": zaakeigenschap.uuid},
        )
        zaak_url = reverse("zaak-detail", kwargs={"version": 1, "uuid": zaak.uuid},)

        zaakeigenschap_data = {
            "zaak": f"http://example.com{zaak_url}",
            "eigenschap": EIGENSCHAP2,
            "waarde": "This is a changed value",
        }

        response = self.client.patch(zaakeigenschap_url, data=zaakeigenschap_data)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        invalid_params = response.json()["invalidParams"]

        self.assertEqual(1, len(invalid_params))

        self.assertEqual("eigenschap", invalid_params[0]["name"])
        self.assertEqual("wijzigen-niet-toegelaten", invalid_params[0]["code"])

    def test_cannot_change_zaak(self):
        zaak1 = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak2 = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaakeigenschap = ZaakEigenschapFactory.create(
            zaak=zaak1, eigenschap=EIGENSCHAP, waarde="This is a value"
        )

        zaakeigenschap_url = reverse(
            "zaakeigenschap-detail",
            kwargs={"version": 1, "zaak_uuid": zaak1.uuid, "uuid": zaakeigenschap.uuid},
        )
        zaak2_url = reverse("zaak-detail", kwargs={"version": 1, "uuid": zaak2.uuid},)

        zaakeigenschap_data = {
            "zaak": f"http://example.com{zaak2_url}",
            "eigenschap": EIGENSCHAP,
            "waarde": "This is a changed value",
        }

        response = self.client.patch(zaakeigenschap_url, data=zaakeigenschap_data)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        invalid_params = response.json()["invalidParams"]

        self.assertEqual(1, len(invalid_params))

        self.assertIn("zaak", invalid_params[0]["name"])
        self.assertEqual("wijzigen-niet-toegelaten", invalid_params[0]["code"])

    def test_zaak_eigenschappen_partial_update_without_eigenschap(self):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaakeigenschap = ZaakEigenschapFactory.create(
            zaak=zaak, eigenschap=EIGENSCHAP, waarde="This is a value"
        )

        zaakeigenschap_url = reverse(
            "zaakeigenschap-detail",
            kwargs={"version": 1, "zaak_uuid": zaak.uuid, "uuid": zaakeigenschap.uuid},
        )

        zaakeigenschap_data = {
            "waarde": "This is a changed value",
        }

        response = self.client.patch(zaakeigenschap_url, data=zaakeigenschap_data)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        zaakeigenschap.refresh_from_db()

        self.assertEqual("This is a changed value", zaakeigenschap.waarde)

    def test_delete(self):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaakeigenschap = ZaakEigenschapFactory.create(
            zaak=zaak, eigenschap=EIGENSCHAP, waarde="This is a value"
        )

        zaakeigenschap_url = reverse(
            "zaakeigenschap-detail",
            kwargs={"version": 1, "zaak_uuid": zaak.uuid, "uuid": zaakeigenschap.uuid},
        )

        self.assertEqual(1, ZaakEigenschap.objects.all().count())

        response = self.client.delete(zaakeigenschap_url)

        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        self.assertEqual(0, ZaakEigenschap.objects.all().count())
