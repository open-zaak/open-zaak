# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.tests.utils import JWTAuthMixin

from ...catalogi.tests.factories import ZaakTypeFactory
from .factories import ZaakFactory
from .utils import ZAAK_WRITE_KWARGS, get_operation_url


class ZaakOpschortingTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_eerdere_opschorting_field_cannot_be_changed(self):
        zaak = ZaakFactory.create(
            opschorting_indicatie=False, opschorting_eerdere_opschorting=False
        )
        zaak_url = reverse(zaak)

        response = self.client.patch(
            zaak_url,
            {
                "opschorting": {
                    "indicatie": True,
                    "eerdereOpschorting": False,
                    "reden": "test",
                }
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["opschorting"],
            {"indicatie": True, "eerdereOpschorting": True, "reden": "test"},
        )

    def test_eerdere_opschorting_stays(self):
        zaak = ZaakFactory.create(opschorting_indicatie=True)

        self.assertTrue(zaak.opschorting_eerdere_opschorting)

        zaak_url = reverse(zaak)

        response = self.client.patch(
            zaak_url,
            {"opschorting": {"indicatie": False, "reden": ""}},
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["opschorting"],
            {"indicatie": False, "eerdereOpschorting": True, "reden": ""},
        )

    def test_eerdere_opschorting_stays_with_null(self):
        zaak = ZaakFactory.create(opschorting_indicatie=True)

        self.assertTrue(zaak.opschorting_eerdere_opschorting)

        zaak_url = reverse(zaak)

        response = self.client.patch(
            zaak_url,
            {"opschorting": None},
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["opschorting"],
            {"indicatie": False, "eerdereOpschorting": True, "reden": ""},
        )

    def test_create_zaak_with_opschorting(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
            "toelichting": "test",
            "opschorting": {"indicatie": True, "reden": "test"},
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(
            response.json()["opschorting"],
            {"indicatie": True, "eerdereOpschorting": True, "reden": "test"},
        )
