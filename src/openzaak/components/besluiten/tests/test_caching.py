# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2023 Dimpact

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.tests.utils import JWTAuthMixin

from ..constants import VervalRedenen
from ..models import Besluit
from .factories import BesluitFactory


@override_settings(ALLOWED_HOSTS=["testserver", "openzaak.nl"])
class BesluitCreateTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_besluit_cachalot(self):
        """
        Assert that the zaak list cache is invalidated when a new Zaak is created
        """
        url = reverse(Besluit)
        besluittype = BesluitTypeFactory.create(concept=False)
        besluittype_url = reverse(besluittype)
        BesluitFactory.create()

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        response = self.client.post(
            url,
            {
                "verantwoordelijke_organisatie": "517439943",  # RSIN
                "identificatie": "123123",
                "besluittype": f"http://testserver{besluittype_url}",
                "datum": "2018-09-06",
                "toelichting": "Vergunning verleend.",
                "ingangsdatum": "2018-10-01",
                "vervaldatum": "2018-11-01",
                "vervalreden": VervalRedenen.tijdelijk,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # re-request list
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
