# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Als gemeente wil ik dat de aanvraag tbh een straatoptreden als zaak wordt
gecreëerd zodat mijn dossiervorming op orde is en de voortgang transparant is.

Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/163

Zie ook: test_userstory_39.py, test_userstory_169.py
"""
from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.utils.tests import JWTAuthMixin

from .utils import ZAAK_WRITE_KWARGS, get_operation_url

# aanvraag aangemaakt in extern systeem, leeft buiten ZRC
VERANTWOORDELIJKE_ORGANISATIE = "517439943"


class US169TestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_create_aanvraag(self):
        """
        Maak een zaak voor een aanvraag.
        """
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        zaak_create_url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "identificatie": "HLM-straatartiest-42",
            "omschrijving": "Dagontheffing - Station Haarlem",
            "toelichting": "Het betreft een clown met grote trom, mondharmonica en cymbalen.",
            "startdatum": "2018-08-15",
        }

        # aanmaken zaak
        response = self.client.post(zaak_create_url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.json()
        self.assertIn("identificatie", data)
        self.assertEqual(data["registratiedatum"], date.today().strftime("%Y-%m-%d"))
        self.assertEqual(data["startdatum"], "2018-08-15")
