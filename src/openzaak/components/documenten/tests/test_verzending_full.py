# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse, reverse_lazy

from openzaak.tests.utils import JWTAuthMixin

from ..models import Verzending
from .factories import VerzendingFactory


class VerzendingAPITests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_list(self):
        """
        test pagination and ordering here, individual attributes are checked in test_read_* methods below
        """
        url = reverse(Verzending)
        verzending1, verzending2, verzending3 = VerzendingFactory.create_batch(3)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(response_data["count"], 3)
        self.assertEqual(
            response_data["results"][0]["url"],
            f"http://testserver{reverse(verzending3)}",
        )
        self.assertEqual(
            response_data["results"][1]["url"],
            f"http://testserver{reverse(verzending2)}",
        )
        self.assertEqual(
            response_data["results"][2]["url"],
            f"http://testserver{reverse(verzending1)}",
        )

    def test_read_with_inner_address(self):
        verzending = VerzendingFactory.create(has_inner_address=True)
        url = reverse(verzending)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "url": f"http://testserver{url}",
                "betrokkene": verzending.betrokkene,
                "informatieobject": f"http://testserver{reverse(verzending.get_informatieobject())}",
                "aardRelatie": verzending.aard_relatie,
                "toelichting": verzending.toelichting,
                "ontvangstdatum": verzending.ontvangstdatum,
                "verzenddatum": verzending.verzenddatum,
                "contactPersoon": verzending.contact_persoon,
                "contactpersoonnaam": verzending.contactpersoonnaam,
                "binnenlandsCorrespondentieadres": {
                    "huisletter": verzending.binnenlands_correspondentieadres_huisletter,
                    "huisnummer": verzending.binnenlands_correspondentieadres_huisnummer,
                    "huisnummerToevoeging": verzending.binnenlands_correspondentieadres_huisnummer_toevoeging,
                    "naamOpenbareRuimte": verzending.binnenlands_correspondentieadres_naam_openbare_ruimte,
                    "postcode": verzending.binnenlands_correspondentieadres_postcode,
                    "woonplaatsnaam": verzending.binnenlands_correspondentieadres_woonplaats,
                },
                "buitenlandsCorrespondentieadres": {
                    "adresBuitenland_1": "",
                    "adresBuitenland_2": "",
                    "adresBuitenland_3": "",
                    "landPostadres": "",
                },
                "correspondentiePostadres": {
                    "postBusOfAntwoordnummer": None,
                    "postadresPostcode": "",
                    "postadresType": "",
                    "woonplaatsnaam": "",
                },
                "faxnummer": verzending.faxnummer,
                "emailadres": verzending.emailadres,
                "mijnOverheid": verzending.mijn_overheid,
                "telefoonnummer": verzending.telefoonnummer,
            },
        )

    def test_read_with_outer_address(self):
        pass

    def test_read_with_post_address(self):
        pass

    def test_create_with_inner_address(self):
        pass

    def test_create_with_outer_address(self):
        pass

    def test_create_with_post_address(self):
        pass

    def test_create_no_address_fail(self):
        pass

    def test_create_more_than_one_address_fail(self):
        pass

    def test_update(self):
        pass

    def test_update_no_address_fail(self):
        pass

    def test_update_more_than_one_address_fail(self):
        pass

    def test_partial_update(self):
        pass

    def test_partial_update_same_address(self):
        pass

    def test_partial_update_other_address_fail(self):
        pass

    def test_delete(self):
        pass


class VerzendingFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    url = reverse_lazy(Verzending)

    def test_list_filter_by_informatieobject(self):
        pass

    def test_list_filter_by_betrokkene(self):
        pass

    def test_list_filter_by_aard_relatie(self):
        pass

    def test_list_filter_combined(self):
        pass

    def test_list_filter_by_unknown_parameter(self):
        pass
