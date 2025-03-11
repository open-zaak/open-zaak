# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2025 Dimpact
from datetime import date

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import RolTypes
from vng_api_common.tests import TypeCheckMixin, get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import RolTypeFactory, ZaakTypeFactory
from openzaak.tests.utils import JWTAuthMixin

from ..models import Rol
from .factories import RolFactory, ZaakFactory
from .utils import get_operation_url

BETROKKENE = (
    "http://www.some-api.org/api/betrokkene/8768c581-2817-4fe5-933d-37af92d819dd"
)


@freeze_time("2025-01-01T12:00:00")
class RolGeldigheidTestCase(JWTAuthMixin, TypeCheckMixin, APITestCase):
    heeft_alle_autorisaties = True
    maxDiff = None
    list_url = get_operation_url("rol_create")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaaktype = ZaakTypeFactory.create()
        cls.roltype = RolTypeFactory.create(zaaktype=cls.zaaktype)
        cls.roltype_url = reverse(cls.roltype)
        cls.zaak = ZaakFactory.create(zaaktype=cls.zaaktype)
        cls.zaak_url = reverse(cls.zaak)

    def test_create_rol_with_geldigheid(self):
        data = {
            "zaak": f"http://testserver{self.zaak_url}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.medewerker,
            "roltype": f"http://testserver{self.roltype_url}",
            "roltoelichting": "foo",
            "beginGeldigheid": "2025-01-01",
            "eindeGeldigheid": "2025-02-01",
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rol.objects.count(), 1)

        rol = Rol.objects.get()

        self.assertEqual(rol.begin_geldigheid, date(2025, 1, 1))
        self.assertEqual(rol.einde_geldigheid, date(2025, 2, 1))

    def test_create_rol_with_begin_geldigheid_without_einde_geldigheid(self):
        data = {
            "zaak": f"http://testserver{self.zaak_url}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.medewerker,
            "roltype": f"http://testserver{self.roltype_url}",
            "roltoelichting": "foo",
            "beginGeldigheid": "2025-01-01",
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Rol.objects.count(), 1)

        rol = Rol.objects.get()

        self.assertEqual(rol.begin_geldigheid, date(2025, 1, 1))
        self.assertEqual(rol.einde_geldigheid, None)

    def test_create_rol_with_einde_geldigheid_cannot_be_before_begin_geldigheid(self):
        data = {
            "zaak": f"http://testserver{self.zaak_url}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.medewerker,
            "roltype": f"http://testserver{self.roltype_url}",
            "roltoelichting": "foo",
            "beginGeldigheid": "2025-01-01",
            "eindeGeldigheid": "2024-01-01",
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Rol.objects.count(), 0)

        validation_error = get_validation_errors(response, "eindeGeldigheid")

        self.assertEqual(
            validation_error["code"], "einde-geldigheid-before-begin-geldigheid"
        )

    def test_update_rol_with_einde_geldigheid_cannot_be_before_begin_geldigheid(self):
        rol = RolFactory.create(roltype=self.roltype)
        data = {
            "zaak": f"http://testserver{self.zaak_url}",
            "betrokkene": BETROKKENE,
            "betrokkene_type": RolTypes.medewerker,
            "roltype": f"http://testserver{self.roltype_url}",
            "roltoelichting": "foo",
            "beginGeldigheid": "2025-01-01",
            "eindeGeldigheid": "2024-01-01",
        }

        response = self.client.put(reverse(rol), data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, "eindeGeldigheid")

        self.assertEqual(
            validation_error["code"], "einde-geldigheid-before-begin-geldigheid"
        )
