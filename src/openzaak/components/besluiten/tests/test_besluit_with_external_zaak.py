# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.tests.utils import (
    get_zaak_response,
    get_zaakbesluit_response,
)
from openzaak.tests.utils import mock_service_oas_get
from openzaak.utils.tests import JWTAuthMixin

from ..constants import VervalRedenen
from ..models import Besluit
from .factories import BesluitFactory
from .utils import get_operation_url


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class BesluitCreateExternalZaakTests(TypeCheckMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    base = "https://externe.catalogus.nl/api/v1/"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        Service.objects.create(
            api_type=APITypes.zrc,
            api_root=cls.base,
            label="external zaken",
            auth_type=AuthTypes.no_auth,
        )

    def _create_besluit(self, zaak: str) -> Besluit:
        besluittype = BesluitTypeFactory.create(concept=False, zaaktypen=[])
        zaaktype = besluittype.zaaktypen.get()
        zaaktype_url = f"http://testserver{reverse(zaaktype)}"
        zaakbesluit_data = get_zaakbesluit_response(zaak)

        # create besluit
        with requests_mock.Mocker(real_http=True) as m:
            m.get(zaak, json=get_zaak_response(zaak, zaaktype_url))
            m.post(f"{zaak}/besluiten", json=zaakbesluit_data)
            besluit = BesluitFactory.create(
                zaak=zaak,
                besluittype=besluittype,
                _zaakbesluit_url=zaakbesluit_data["url"],
            )
        return besluit

    def test_create_with_external_zaak(self):
        zaak = f"{self.base}zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        besluittype = BesluitTypeFactory.create(concept=False)
        zaaktype = ZaakTypeFactory.create(
            concept=False, catalogus=besluittype.catalogus
        )
        zaaktype.besluittypen.add(besluittype)
        zaaktype_url = f"http://testserver{reverse(zaaktype)}"
        zaakbesluit_data = get_zaakbesluit_response(zaak)
        url = get_operation_url("besluit_create")

        with requests_mock.Mocker(real_http=True) as m:
            mock_service_oas_get(m, APITypes.zrc, self.base)
            m.get(zaak, json=get_zaak_response(zaak, zaaktype_url))
            m.post(f"{zaak}/besluiten", json=zaakbesluit_data, status_code=201)

            response = self.client.post(
                url,
                {
                    "verantwoordelijke_organisatie": "517439943",
                    "identificatie": "123123",
                    "besluittype": f"http://testserver{reverse(besluittype)}",
                    "datum": "2018-09-06",
                    "toelichting": "Vergunning verleend.",
                    "ingangsdatum": "2018-10-01",
                    "vervaldatum": "2018-11-01",
                    "vervalreden": VervalRedenen.tijdelijk,
                    "zaak": zaak,
                },
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        besluit = Besluit.objects.get()
        besluit_url = f"http://testserver{reverse(besluit)}"
        self.assertEqual(besluit._zaakbesluit_url, zaakbesluit_data["url"])

        history_post = [
            req
            for req in m.request_history
            if req.method == "POST" and req.url == f"{zaak}/besluiten"
        ]
        self.assertEqual(len(history_post), 1)
        self.assertEqual(history_post[0].json(), {"besluit": besluit_url})

    def test_create_with_external_zaak_fail_create_zaakbesluit(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        zaaktype = ZaakTypeFactory.create(
            concept=False, catalogus=besluittype.catalogus
        )
        zaaktype.besluittypen.add(besluittype)
        zaaktype_url = f"http://testserver{reverse(zaaktype)}"

        zaak = f"{self.base}zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        url = get_operation_url("besluit_create")

        with requests_mock.Mocker(real_http=True) as m:
            mock_service_oas_get(m, APITypes.zrc, self.base)
            m.get(zaak, json=get_zaak_response(zaak, zaaktype_url))
            m.post(f"{zaak}/besluiten", status_code=404, text="Not Found")

            response = self.client.post(
                url,
                {
                    "verantwoordelijke_organisatie": "517439943",
                    "identificatie": "123123",
                    "besluittype": f"http://testserver{reverse(besluittype)}",
                    "datum": "2018-09-06",
                    "toelichting": "Vergunning verleend.",
                    "ingangsdatum": "2018-10-01",
                    "vervaldatum": "2018-11-01",
                    "vervalreden": VervalRedenen.tijdelijk,
                    "zaak": zaak,
                },
            )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "zaak")
        self.assertEqual(error["code"], "pending-relations")

    def test_update_external_zaak(self):
        zaak_old = f"{self.base}zaken/{uuid.uuid4()}"
        besluit = self._create_besluit(zaak_old)
        zaaktype = besluit.besluittype.zaaktypen.get()
        zaaktype_url = f"http://testserver{reverse(zaaktype)}"
        old_zaakbesluit_url = besluit._zaakbesluit_url

        # update zaak in the besluit
        zaak_new = f"{self.base}zaken/{uuid.uuid4()}"
        zaakbesluit_new_data = get_zaakbesluit_response(zaak_new)
        besluit_url = f"http://testserver{reverse(besluit)}"

        with requests_mock.Mocker(real_http=True) as m:
            mock_service_oas_get(m, APITypes.zrc, self.base)
            m.get(zaak_old, json=get_zaak_response(zaak_old, zaaktype_url))
            m.get(zaak_new, json=get_zaak_response(zaak_new, zaaktype_url))
            m.delete(old_zaakbesluit_url, status_code=204)
            m.post(f"{zaak_new}/besluiten", json=zaakbesluit_new_data, status_code=201)

            response = self.client.patch(besluit_url, {"zaak": zaak_new})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        besluit.refresh_from_db()

        self.assertEqual(besluit._previous_zaak_url, zaak_old)
        self.assertEqual(besluit._zaak_url, zaak_new)
        self.assertEqual(besluit._zaakbesluit_url, zaakbesluit_new_data["url"])

        history_post = [
            req
            for req in m.request_history
            if req.method == "POST" and req.url == f"{zaak_new}/besluiten"
        ]
        self.assertEqual(len(history_post), 1)
        self.assertEqual(history_post[0].json(), {"besluit": besluit_url})

        history_delete = [
            req
            for req in m.request_history
            if req.method == "DELETE" and req.url == old_zaakbesluit_url
        ]
        self.assertEqual(len(history_delete), 1)

    def test_update_external_zaak_fail_delete_zaakbesluit(self):
        zaak_old = f"{self.base}zaken/{uuid.uuid4()}"
        besluit = self._create_besluit(zaak_old)
        zaaktype = besluit.besluittype.zaaktypen.get()
        zaaktype_url = f"http://testserver{reverse(zaaktype)}"
        old_zaakbesluit_url = besluit._zaakbesluit_url

        # update zaak in the besluit
        zaak_new = f"{self.base}zaken/{uuid.uuid4()}"
        zaakbesluit_new_data = get_zaakbesluit_response(zaak_new)
        besluit_url = f"http://testserver{reverse(besluit)}"

        with requests_mock.Mocker(real_http=True) as m:
            mock_service_oas_get(m, APITypes.zrc, self.base)
            m.get(zaak_old, json=get_zaak_response(zaak_old, zaaktype_url))
            m.get(zaak_new, json=get_zaak_response(zaak_new, zaaktype_url))
            m.delete(old_zaakbesluit_url, status_code=404, text="not found")
            m.post(f"{zaak_new}/besluiten", json=zaakbesluit_new_data, status_code=201)

            response = self.client.patch(besluit_url, {"zaak": zaak_new})

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "zaak")
        self.assertEqual(error["code"], "pending-relations")

    def test_delete_with_external_zaak(self):
        zaak = f"{self.base}zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        besluit = self._create_besluit(zaak)
        besluit_url = f"http://testserver{reverse(besluit)}"
        zaakbesluit_url = besluit._zaakbesluit_url
        zaaktype = besluit.besluittype.zaaktypen.get()
        zaaktype_url = f"http://testserver{reverse(zaaktype)}"

        with requests_mock.Mocker(real_http=True) as m:
            mock_service_oas_get(m, APITypes.zrc, self.base)
            m.get(zaak, json=get_zaak_response(zaak, zaaktype_url))
            m.delete(zaakbesluit_url, status_code=204)

            response = self.client.delete(besluit_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        self.assertEqual(Besluit.objects.count(), 0)

        history_delete = [
            req
            for req in m.request_history
            if req.method == "DELETE" and req.url == zaakbesluit_url
        ]
        self.assertEqual(len(history_delete), 1)

    def test_delete_with_external_zaak_fail_delete_zaakbesluit(self):
        zaak = f"{self.base}zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        besluit = self._create_besluit(zaak)
        besluit_url = f"http://testserver{reverse(besluit)}"
        zaakbesluit_url = besluit._zaakbesluit_url
        zaaktype = besluit.besluittype.zaaktypen.get()
        zaaktype_url = f"http://testserver{reverse(zaaktype)}"

        with requests_mock.Mocker(real_http=True) as m:
            mock_service_oas_get(m, APITypes.zrc, self.base)
            m.get(zaak, json=get_zaak_response(zaak, zaaktype_url))
            m.delete(zaakbesluit_url, status_code=404, text="Not found")

            response = self.client.delete(besluit_url)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "zaak")
        self.assertEqual(error["code"], "pending-relations")
