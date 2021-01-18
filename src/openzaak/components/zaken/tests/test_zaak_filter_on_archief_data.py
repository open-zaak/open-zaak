# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/348
"""
from datetime import date
from urllib.parse import quote_plus, urlencode

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import Archiefnominatie, Archiefstatus

from openzaak.utils.tests import JWTAuthMixin

from .factories import ZaakFactory
from .utils import ZAAK_WRITE_KWARGS, get_operation_url


class US345TestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_filter_on_archiefactiedatum_archiefnominatie_archiefstatus(self):
        zaak_1 = ZaakFactory.create(
            archiefnominatie=Archiefnominatie.blijvend_bewaren,
            archiefactiedatum=date(2010, 1, 1),
            archiefstatus=Archiefstatus.nog_te_archiveren,
        )
        ZaakFactory.create(
            archiefnominatie=Archiefnominatie.vernietigen,
            archiefactiedatum=date(2010, 1, 1),
            archiefstatus=Archiefstatus.nog_te_archiveren,
        )

        zaak_list_url = get_operation_url("zaak_list")

        query_params = {
            "archiefactiedatum__lt": date(2015, 1, 1),
            "archiefnominatie": Archiefnominatie.blijvend_bewaren,
            "archiefstatus__in": ",".join(
                [Archiefstatus.nog_te_archiveren, Archiefstatus.gearchiveerd]
            ),
        }
        query_params = urlencode(query_params, quote_via=quote_plus)

        response = self.client.get(
            f"{zaak_list_url}?{query_params}", **ZAAK_WRITE_KWARGS
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()["results"]
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0]["url"].endswith(str(zaak_1.uuid)))
