# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Als straatartiest wil ik dat mijn aanvraag een uniek volgnummer krijgt zodat
ik in mijn communicatie snel kan verwijzen naar mijn aanvraag.

Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/164
"""
from django.test import override_settings
from django.utils.translation import gettext_lazy as _

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import ZaakTypeFactory
from openzaak.tests.utils import JWTAuthMixin

from ..models import Zaak
from .factories import ZaakFactory
from .utils import ZAAK_WRITE_KWARGS, get_operation_url

VERANTWOORDELIJKE_ORGANISATIE = "517439943"


class US164TestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_geef_zelf_identificatie(self):
        """
        Garandeer dat de client zelf een identificatie kan genereren.
        """
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "identificatie": "strtmzk-0001",
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "bronorganisatie": "517439943",
            "startdatum": "2018-06-11",
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak = Zaak.objects.get()
        self.assertEqual(zaak.identificatie, "strtmzk-0001")

    def test_uniqueness_identificatie(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        ZaakFactory.create(identificatie="strtmzk-0001", bronorganisatie="517439943")

        url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "identificatie": "strtmzk-0001",
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "startdatum": "2018-06-11",
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "invalid")

        error = get_validation_errors(response, "identificatie")
        self.assertEqual(error["code"], "identificatie-niet-uniek")
        self.assertEqual(
            error["reason"],
            _(
                "Deze identificatie ({identificatie}) bestaat al voor deze bronorganisatie"
            ).format(identificatie="strtmzk-0001"),
        )

    @override_settings(ZAAK_IDENTIFICATIE_GENERATOR="use-start-datum-year")
    @freeze_time("2025-1-1")
    def test_zaak_identificatie_with_startdatum(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "bronorganisatie": "517439943",
            "startdatum": "2030-06-11",
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak = Zaak.objects.get()
        self.assertEqual(zaak.identificatie, "ZAAK-2030-0000000001")

    @override_settings(ZAAK_IDENTIFICATIE_GENERATOR="abc")
    @freeze_time("2025-1-1")
    def test_zaak_identificatie_with_invalid_generator_uses_startdatum(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "bronorganisatie": "517439943",
            "startdatum": "2030-06-11",
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak = Zaak.objects.get()
        self.assertEqual(zaak.identificatie, "ZAAK-2030-0000000001")

    @override_settings(ZAAK_IDENTIFICATIE_GENERATOR="use-creation-year")
    @freeze_time("2025-1-1")
    def test_zaak_identificatie_with_creation_year(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        url = get_operation_url("zaak_create")
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "verantwoordelijkeOrganisatie": VERANTWOORDELIJKE_ORGANISATIE,
            "bronorganisatie": "517439943",
            "startdatum": "2018-06-11",
        }

        response = self.client.post(url, data, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        zaak = Zaak.objects.get()
        self.assertEqual(zaak.identificatie, "ZAAK-2025-0000000001")
