# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import RolTypes
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse

from openzaak.tests.utils import JWTAuthMixin, mock_ztc_oas_get

from ..models import Medewerker, NatuurlijkPersoon
from .factories import RolFactory, ZaakFactory
from .utils import get_roltype_response, get_zaaktype_response

BETROKKENE = (
    "http://www.example.org/api/betrokkene/8768c581-2817-4fe5-933d-37af92d819dd"
)


@override_settings(ALLOWED_HOSTS=["testserver"])
class RolTestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None

    def test_update_rol_without_identificatie(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            roltype__zaaktype=zaak.zaaktype,
            betrokkene="http://www.example.org/api/betrokkene/old",
            roltoelichting="old",
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(rol.roltype)}",
            "roltoelichting": "new",
        }

        response = self.client.put(reverse(rol), data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        rol.refresh_from_db()

        self.assertEqual(rol.betrokkene, BETROKKENE)
        self.assertEqual(rol.roltoelichting, "new")

    def test_update_rol_with_identificatie(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            roltype__zaaktype=zaak.zaaktype,
            betrokkene="",
            betrokkene_type=RolTypes.medewerker,
            roltoelichting="old",
        )
        Medewerker.objects.create(rol=rol, identificatie="123456")
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(rol.roltype)}",
            "roltoelichting": "new",
            "betrokkeneIdentificatie": {
                "anpIdentificatie": "12345",
            },
        }

        response = self.client.put(reverse(rol), data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        rol.refresh_from_db()

        self.assertEqual(rol.betrokkene_type, RolTypes.natuurlijk_persoon)
        self.assertEqual(rol.roltoelichting, "new")
        self.assertEqual(NatuurlijkPersoon.objects.count(), 1)
        self.assertEqual(Medewerker.objects.count(), 0)

        natuurlijk_persoon = NatuurlijkPersoon.objects.get()

        self.assertEqual(rol.natuurlijkpersoon, natuurlijk_persoon)
        self.assertEqual(natuurlijk_persoon.anp_identificatie, "12345")

    def test_update_rol_from_betrokkene_identificatie_to_betrokkene(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            roltype__zaaktype=zaak.zaaktype,
            betrokkene="",
            betrokkene_type=RolTypes.medewerker,
            roltoelichting="old",
        )
        Medewerker.objects.create(rol=rol, identificatie="123456")
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkene_type": RolTypes.medewerker,
            "roltype": f"http://testserver{reverse(rol.roltype)}",
            "betrokkene": BETROKKENE,
            "roltoelichting": "new",
        }

        response = self.client.put(reverse(rol), data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        rol.refresh_from_db()

        self.assertEqual(rol.roltoelichting, "new")
        self.assertEqual(rol.betrokkene, BETROKKENE)
        self.assertEqual(Medewerker.objects.count(), 0)

    def test_update_rol_fail_validation(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            roltype__zaaktype=zaak.zaaktype,
            betrokkene=BETROKKENE,
            roltoelichting="old",
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": f"http://testserver{reverse(rol.roltype)}",
            "roltoelichting": "new",
        }

        response = self.client.put(reverse(rol), data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "nonFieldErrors")

        self.assertEqual(validation_error["code"], "invalid-betrokkene")

    @tag("external-urls")
    def test_update_rol_with_external_roltype(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"
        roltype = "https://externe.catalogus.nl/api/v1/roltypen/b923543f-97aa-4a55-8c20-889b5906cf75"
        zaak = ZaakFactory.create(zaaktype=zaaktype)
        rol = RolFactory.create(
            zaak=zaak,
            roltype=roltype,
            betrokkene="http://www.example.org/api/betrokkene/old",
            roltoelichting="old",
        )
        data = {
            "zaak": f"http://testserver{reverse(zaak)}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.natuurlijk_persoon,
            "roltype": roltype,
            "roltoelichting": "new",
        }

        with requests_mock.Mocker() as m:
            mock_ztc_oas_get(m)
            m.get(zaaktype, json=get_zaaktype_response(catalogus, zaaktype))
            m.get(roltype, json=get_roltype_response(roltype, zaaktype))

            response = self.client.put(reverse(rol), data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        rol.refresh_from_db()
        self.assertEqual(rol.roltoelichting, "new")

    def test_patch_rol_not_allowed(self):
        zaak = ZaakFactory.create()
        rol = RolFactory.create(
            zaak=zaak,
            roltype__zaaktype=zaak.zaaktype,
            betrokkene="http://www.example.org/api/betrokkene/old",
            roltoelichting="old",
        )

        response = self.client.patch(
            reverse(rol),
            {
                "roltoelichting": "new",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
