from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.tests.utils import (
    get_zaak_response,
    get_zaakbesluit_response,
)
from openzaak.utils.tests import JWTAuthMixin

from ..constants import VervalRedenen
from ..models import Besluit
from .utils import get_operation_url


@tag("external-urls")
@override_settings(ALLOWED_HOSTS=["testserver"])
class BesluitCreateExternalzaakTests(TypeCheckMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_create_with_external_zaak(self):
        zaak = "https://externe.catalogus.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        besluittype = BesluitTypeFactory.create(concept=False)
        zaaktype = ZaakTypeFactory.create(
            concept=False, catalogus=besluittype.catalogus
        )
        zaaktype.besluittypen.add(besluittype)
        zaaktype_url = f"http://testserver{reverse(zaaktype)}"
        zaakbesluit_data = get_zaakbesluit_response(zaak)
        url = get_operation_url("besluit_create")

        with requests_mock.Mocker(real_http=True) as m:
            m.get(zaak, json=get_zaak_response(zaak, zaaktype_url))
            m.post(f"{zaak}/besluiten", json=zaakbesluit_data)

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

        history_post = [req for req in m.request_history if req.method == "POST" and req.url == f"{zaak}/besluiten"]
        self.assertEqual(len(history_post), 1)
        self.assertEqual(history_post[0].json(), {"besluit": besluit_url})

    def test_create_with_external_zaak_fail_create_zaakbesluit(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        zaaktype = ZaakTypeFactory.create(
            concept=False, catalogus=besluittype.catalogus
        )
        zaaktype.besluittypen.add(besluittype)
        zaaktype_url = f"http://testserver{reverse(zaaktype)}"

        zaak = "https://externe.catalogus.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        url = get_operation_url("besluit_create")

        with requests_mock.Mocker(real_http=True) as m:
            m.get(zaak, json=get_zaak_response(zaak, zaaktype_url))
            m.post(f"{zaak}/besluiten", status_code=404, text='Not Found')

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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        error = get_validation_errors(response, "zaak")
        self.assertEqual(error['code'], 'pending-relations')

    def test_update_external_zaak(self):
        besluittype = BesluitTypeFactory.create(concept=False)
        zaaktype = ZaakTypeFactory.create(
            concept=False, catalogus=besluittype.catalogus
        )
        zaaktype.besluittypen.add(besluittype)
        zaaktype_url = f"http://testserver{reverse(zaaktype)}"
        zaak_old = "https://externe.catalogus.nl/api/v1/zaken/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaakbesluit_old_data = get_zaakbesluit_response(zaak_old)
        url = get_operation_url("besluit_create")

        # create besluit
        with requests_mock.Mocker(real_http=True) as m:
            m.get(zaak_old, json=get_zaak_response(zaak_old, zaaktype_url))
            m.post(f"{zaak_old}/besluiten", json=zaakbesluit_old_data)

            response_create = self.client.post(
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
                    "zaak": zaak_old,
                },
            )
        self.assertEqual(response_create.status_code, status.HTTP_201_CREATED, response_create.data)

        besluit = Besluit.objects.get()
        besluit_url = f"http://testserver{reverse(besluit)}"
        zaak_new = "https://externe.catalogus.nl/api/v1/zaken/19b702ce-1387-42a3-87d9-b070e8c3f43d"
        zaakbesluit_new_data = get_zaakbesluit_response(zaak_new)

        # update zaak in the besluit
        with requests_mock.Mocker(real_http=True) as m:
            m.get(zaak_old, json=get_zaak_response(zaak_old, zaaktype_url))
            m.get(zaak_new, json=get_zaak_response(zaak_new, zaaktype_url))
            m.delete(besluit._zaakbesluit_url)
            m.post(f"{zaak_new}/besluiten", json=zaakbesluit_new_data)

            response_update = self.client.patch(besluit_url, {"zaak": zaak_new})

        self.assertEqual(response_update.status_code, status.HTTP_200_OK, response_update.data)



    def test_update_external_zaak_fail_update_zaakbesluit(self):
        # TODO
        pass

    def test_delete_with_external_zaak(self):
        # TODO
        pass

    def test_delete_with_external_zaak_fail_delete_zaakbesluit(self):
        # TODO
        pass
