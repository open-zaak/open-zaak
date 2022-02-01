# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
"""
Guarantee that the proper authorization machinery is in place for roles.
"""
from django.contrib.gis.geos import Point
from django.test import override_settings, tag

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.audittrails.api.scopes import SCOPE_AUDITTRAILS_LEZEN
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.authorizations.models import Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import TypeCheckMixin, reverse

from openzaak.components.autorisaties.tests.factories import RoleFactory
from openzaak.components.besluiten.tests.factories import BesluitFactory
from openzaak.components.catalogi.tests.factories import (
    EigenschapFactory,
    ZaakTypeFactory,
)
from openzaak.components.zaken.models import Zaak, ZaakBesluit
from openzaak.utils.tests import JWTAuthMixin, generate_jwt_auth

from ..api.scopes import (
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
)
from .constants import POLYGON_AMSTERDAM_CENTRUM
from .factories import ZaakEigenschapFactory, ZaakFactory
from .utils import (
    ZAAK_READ_KWARGS,
    ZAAK_WRITE_KWARGS,
    get_catalogus_response,
    get_operation_url,
    get_zaaktype_response,
)


@tag("api_roles")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakListRoleTests(JWTAuthMixin, TypeCheckMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_BIJWERKEN]
    component = ComponentTypes.zrc
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.confidentieel

    def setUp(self):
        super().setUp()
        token = generate_jwt_auth(
            self.client_id,
            self.secret,
            user_id=self.user_id,
            user_representation=self.user_representation,
            roles=["role1"],
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype2 = ZaakTypeFactory.create(concept=False)
        super().setUpTestData()

        Autorisatie.objects.create(
            applicatie=cls.applicatie,
            component=cls.component,
            scopes=cls.scopes,
            zaaktype=cls.check_for_instance(cls.zaaktype2),
            max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
        )

    def test_zaak_list(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        # The only zaak that should show up
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        # Should not appear
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )
        ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url = reverse("zaak-list")

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["zaaktype"], zaaktype_url)
        self.assertEqual(
            results[0]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

    def test_zaak_list_multiple_roles(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        zaaktype_url2 = f"http://testserver{reverse(self.zaaktype2)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )
        RoleFactory.create(
            name="Role 2",
            slug="role2",
            zaaktype=zaaktype_url2,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        token = generate_jwt_auth(
            self.client_id,
            self.secret,
            user_id=self.user_id,
            user_representation=self.user_representation,
            roles=["role1", "role2"],
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)

        # The only zaak that should show up
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        # Should not appear
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )
        ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )
        url = reverse("zaak-list")

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["zaaktype"], zaaktype_url2)
        self.assertEqual(
            results[0]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.confidentieel,
        )
        self.assertEqual(results[1]["zaaktype"], zaaktype_url)
        self.assertEqual(
            results[1]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

    def test_zaak_list_permissions_cannot_exceed_application_zaaktypen(self):
        zaaktype3 = ZaakTypeFactory.create()
        zaaktype_url3 = f"http://testserver{reverse(zaaktype3)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url3,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        # Should not appear
        ZaakFactory.create(
            zaaktype=zaaktype3,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        url = reverse("zaak-list")

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 0)

    def test_zaak_list_permissions_cannot_exceed_application_vertrouwelijkheidsaanduiding(
        self,
    ):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )
        # Should not appear
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )

        url = reverse("zaak-list")

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 0)

    def test_zaak_list_permissions_cannot_exceed_application_scopes(self,):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )
        # Should not appear
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        self.autorisatie.scopes = []
        self.autorisatie.save()

        url = reverse("zaak-list")

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 0)

    def test_zaak_list_external(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        zaaktype2 = "https://externe.catalogus.nl/api/v1/zaaktypen/b71f72ef-198d-44d8-af64-ae1932df830a"

        Autorisatie.objects.create(
            applicatie=self.applicatie,
            component=self.component,
            scopes=self.scopes,
            zaaktype=zaaktype2,
            max_vertrouwelijkheidaanduiding=self.max_vertrouwelijkheidaanduiding,
        )

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype2,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        # The only zaak that should show up
        ZaakFactory.create(
            zaaktype=zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        # Should not appear
        ZaakFactory.create(
            zaaktype=zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )
        ZaakFactory.create(
            zaaktype=zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url = reverse("zaak-list")

        with requests_mock.Mocker(real_http=True) as m:
            m.register_uri(
                "GET", zaaktype2, json=get_zaaktype_response(catalogus, zaaktype2),
            )
            m.register_uri(
                "GET", catalogus, json=get_catalogus_response(catalogus, zaaktype2),
            )
            response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["zaaktype"], zaaktype2)
        self.assertEqual(
            results[0]["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

    def test_zaakeigenschappen_list(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        ZaakEigenschapFactory.create_batch(3, zaak=zaak1)

        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )
        ZaakEigenschapFactory.create_batch(3, zaak=zaak2)

        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        ZaakEigenschapFactory.create_batch(3, zaak=zaak3)

        url1 = get_operation_url("zaakeigenschap_list", zaak_uuid=zaak1.uuid)
        url2 = get_operation_url("zaakeigenschap_list", zaak_uuid=zaak2.uuid)
        url3 = get_operation_url("zaakeigenschap_list", zaak_uuid=zaak3.uuid)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)
        response3 = self.client.get(url3)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response1.json()), 3)

        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaakeigenschappen_create(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_BIJWERKEN],
            component=ComponentTypes.zrc,
        )

        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        eigenschap1 = EigenschapFactory.create(
            eigenschapnaam="foobar", zaaktype=self.zaaktype
        )
        eigenschap_url1 = reverse(eigenschap1)
        data1 = {
            "zaak": reverse(zaak1),
            "eigenschap": f"http://testserver{eigenschap_url1}",
            "waarde": "overlast_water",
        }

        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )
        data2 = {
            "zaak": reverse(zaak2),
            "eigenschap": f"http://testserver{eigenschap_url1}",
            "waarde": "overlast_water",
        }

        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        eigenschap3 = EigenschapFactory.create(
            eigenschapnaam="foobar", zaaktype=self.zaaktype2
        )
        eigenschap_url3 = reverse(eigenschap3)
        data3 = {
            "zaak": reverse(zaak3),
            "eigenschap": f"http://testserver{eigenschap_url3}",
            "waarde": "overlast_water",
        }

        url1 = get_operation_url("zaakeigenschap_create", zaak_uuid=zaak1.uuid)
        url2 = get_operation_url("zaakeigenschap_create", zaak_uuid=zaak2.uuid)
        url3 = get_operation_url("zaakeigenschap_create", zaak_uuid=zaak3.uuid)

        response1 = self.client.post(url1, data1)
        response2 = self.client.post(url2, data2)
        response3 = self.client.post(url3, data3)

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaakeigenschappen_retrieve(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        zaakeigenschap1 = ZaakEigenschapFactory.create(zaak=zaak1)

        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )
        zaakeigenschap2 = ZaakEigenschapFactory.create(zaak=zaak2)

        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaakeigenschap3 = ZaakEigenschapFactory.create(zaak=zaak3)

        url1 = get_operation_url(
            "zaakeigenschap_read", zaak_uuid=zaak1.uuid, uuid=zaakeigenschap1.uuid
        )
        url2 = get_operation_url(
            "zaakeigenschap_read", zaak_uuid=zaak2.uuid, uuid=zaakeigenschap2.uuid
        )
        url3 = get_operation_url(
            "zaakeigenschap_read", zaak_uuid=zaak3.uuid, uuid=zaakeigenschap3.uuid
        )

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)
        response3 = self.client.get(url3)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaakbesluit_list(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        BesluitFactory.create(zaak=zaak1)

        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )
        BesluitFactory.create(zaak=zaak2)

        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        BesluitFactory.create(zaak=zaak3)

        url1 = get_operation_url("zaakbesluit_list", zaak_uuid=zaak1.uuid)
        url2 = get_operation_url("zaakbesluit_list", zaak_uuid=zaak2.uuid)
        url3 = get_operation_url("zaakbesluit_list", zaak_uuid=zaak3.uuid)

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)
        response3 = self.client.get(url3)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response1.json()), 1)

        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaakbesluit_retrieve(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        BesluitFactory.create(zaak=zaak1)
        zaakbesluit1 = ZaakBesluit.objects.get(zaak=zaak1)

        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )
        BesluitFactory.create(zaak=zaak2)
        zaakbesluit2 = ZaakBesluit.objects.get(zaak=zaak2)

        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        BesluitFactory.create(zaak=zaak3)
        zaakbesluit3 = ZaakBesluit.objects.get(zaak=zaak3)

        url1 = get_operation_url(
            "zaakbesluit_read", zaak_uuid=zaak1.uuid, uuid=zaakbesluit1.uuid
        )
        url2 = get_operation_url(
            "zaakbesluit_read", zaak_uuid=zaak2.uuid, uuid=zaakbesluit2.uuid
        )
        url3 = get_operation_url(
            "zaakbesluit_read", zaak_uuid=zaak3.uuid, uuid=zaakbesluit3.uuid
        )

        response1 = self.client.get(url1)
        response2 = self.client.get(url2)
        response3 = self.client.get(url3)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)


@tag("api_roles")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakRetrieveRoleTests(JWTAuthMixin, TypeCheckMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    component = ComponentTypes.zrc
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.confidentieel

    def setUp(self):
        super().setUp()
        token = generate_jwt_auth(
            self.client_id,
            self.secret,
            user_id=self.user_id,
            user_representation=self.user_representation,
            roles=["role1"],
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype2 = ZaakTypeFactory.create(concept=False)
        super().setUpTestData()

        Autorisatie.objects.create(
            applicatie=cls.applicatie,
            component=cls.component,
            scopes=cls.scopes,
            zaaktype=cls.check_for_instance(cls.zaaktype2),
            max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
        )

    def test_zaak_retrieve(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url1 = reverse(zaak1)
        url2 = reverse(zaak2)
        url3 = reverse(zaak3)

        response1 = self.client.get(url1, **ZAAK_READ_KWARGS)
        response2 = self.client.get(url2, **ZAAK_READ_KWARGS)
        response3 = self.client.get(url3, **ZAAK_READ_KWARGS)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_retrieve_permissions_cannot_exceed_application_zaaktypen(self):
        zaaktype3 = ZaakTypeFactory.create()
        zaaktype_url3 = f"http://testserver{reverse(zaaktype3)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url3,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        # Should not appear
        zaak = ZaakFactory.create(
            zaaktype=zaaktype3,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        url = reverse(zaak)

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_retrieve_permissions_cannot_exceed_application_vertrouwelijkheidsaanduiding(
        self,
    ):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )
        # Should not appear
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )

        url = reverse(zaak)

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_retrieve_permissions_cannot_exceed_application_scopes(self,):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )
        # Should not appear
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        self.autorisatie.scopes = []
        self.autorisatie.save()

        url = reverse(zaak)

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@tag("api_roles")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakCreateRoleTests(JWTAuthMixin, TypeCheckMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_CREATE]
    component = ComponentTypes.zrc
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.confidentieel

    def setUp(self):
        super().setUp()
        token = generate_jwt_auth(
            self.client_id,
            self.secret,
            user_id=self.user_id,
            user_representation=self.user_representation,
            roles=["role1"],
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype2 = ZaakTypeFactory.create(concept=False)
        super().setUpTestData()

        Autorisatie.objects.create(
            applicatie=cls.applicatie,
            component=cls.component,
            scopes=cls.scopes,
            zaaktype=cls.check_for_instance(cls.zaaktype2),
            max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
        )

    def test_zaak_create(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_CREATE],
            component=ComponentTypes.zrc,
        )

        body1 = {
            "zaaktype": f"http://testserver{reverse(self.zaaktype)}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.vertrouwelijk,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
        }

        body2 = {
            "zaaktype": f"http://testserver{reverse(self.zaaktype2)}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
        }
        body3 = {
            "zaaktype": f"http://testserver{reverse(self.zaaktype)}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.confidentieel,
        }

        url = reverse(Zaak)

        response1 = self.client.post(url, body1, **ZAAK_WRITE_KWARGS)
        response2 = self.client.post(url, body2, **ZAAK_WRITE_KWARGS)
        response3 = self.client.post(url, body3, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_create_permissions_cannot_exceed_application_zaaktypen(self):
        zaaktype3 = ZaakTypeFactory.create()
        zaaktype_url3 = f"http://testserver{reverse(zaaktype3)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url3,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        body = {
            "zaaktype": zaaktype_url3,
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.vertrouwelijk,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
        }

        url = reverse(Zaak)

        response = self.client.post(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_create_permissions_cannot_exceed_application_vertrouwelijkheidsaanduiding(
        self,
    ):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        body = {
            "zaaktype": zaaktype_url,
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.zeer_geheim,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
        }

        url = reverse(Zaak)

        response = self.client.post(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_create_permissions_cannot_exceed_application_scopes(self,):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )
        self.autorisatie.scopes = []
        self.autorisatie.save()

        body = {
            "zaaktype": zaaktype_url,
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.zeer_geheim,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
        }

        url = reverse(Zaak)

        response = self.client.post(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@tag("api_roles")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakUpdateRoleTests(JWTAuthMixin, TypeCheckMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_BIJWERKEN]
    component = ComponentTypes.zrc
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.confidentieel

    def setUp(self):
        super().setUp()
        token = generate_jwt_auth(
            self.client_id,
            self.secret,
            user_id=self.user_id,
            user_representation=self.user_representation,
            roles=["role1"],
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype2 = ZaakTypeFactory.create(concept=False)
        super().setUpTestData()

        Autorisatie.objects.create(
            applicatie=cls.applicatie,
            component=cls.component,
            scopes=cls.scopes,
            zaaktype=cls.check_for_instance(cls.zaaktype2),
            max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
        )

    def test_zaak_partial_update(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_BIJWERKEN],
            component=ComponentTypes.zrc,
        )

        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )

        body = {"omschrijving": "aangepast"}

        url1 = reverse(zaak1)
        url2 = reverse(zaak2)
        url3 = reverse(zaak3)

        response1 = self.client.patch(url1, body, **ZAAK_WRITE_KWARGS)
        response2 = self.client.patch(url2, body, **ZAAK_WRITE_KWARGS)
        response3 = self.client.patch(url3, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_partial_update_permissions_cannot_exceed_application_zaaktypen(self):
        zaaktype3 = ZaakTypeFactory.create()
        zaaktype_url3 = f"http://testserver{reverse(zaaktype3)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url3,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak = ZaakFactory.create(
            zaaktype=zaaktype3,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        body = {"omschrijving": "aangepast"}

        url = reverse(zaak)

        response = self.client.patch(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_partial_update_permissions_cannot_exceed_application_vertrouwelijkheidsaanduiding(
        self,
    ):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )

        body = {"omschrijving": "aangepast"}

        url = reverse(zaak)

        response = self.client.patch(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_partial_update_permissions_cannot_exceed_application_scopes(self,):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )
        # Should not appear
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        self.autorisatie.scopes = []
        self.autorisatie.save()

        body = {"omschrijving": "aangepast"}

        url = reverse(zaak)

        response = self.client.patch(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_update(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_BIJWERKEN],
            component=ComponentTypes.zrc,
        )

        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )

        body = {
            "zaaktype": f"http://testserver{reverse(self.zaaktype)}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.vertrouwelijk,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
        }

        url1 = reverse(zaak1)
        url2 = reverse(zaak2)
        url3 = reverse(zaak3)

        response1 = self.client.put(url1, body, **ZAAK_WRITE_KWARGS)
        response2 = self.client.put(url2, body, **ZAAK_WRITE_KWARGS)
        response3 = self.client.put(url3, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_update_permissions_cannot_exceed_application_zaaktypen(self):
        zaaktype3 = ZaakTypeFactory.create()
        zaaktype_url3 = f"http://testserver{reverse(zaaktype3)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url3,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak = ZaakFactory.create(
            zaaktype=zaaktype3,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        body = {
            "zaaktype": zaaktype_url3,
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.vertrouwelijk,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
        }

        url = reverse(zaak)

        response = self.client.put(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_update_permissions_cannot_exceed_application_vertrouwelijkheidsaanduiding(
        self,
    ):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )

        body = {
            "zaaktype": f"http://testserver{reverse(self.zaaktype)}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
        }

        url = reverse(zaak)

        response = self.client.put(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_update_permissions_cannot_exceed_application_scopes(self,):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )
        # Should not appear
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        self.autorisatie.scopes = []
        self.autorisatie.save()

        body = {
            "zaaktype": f"http://testserver{reverse(self.zaaktype)}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.vertrouwelijk,
            "bronorganisatie": "517439943",
            "verantwoordelijkeOrganisatie": "517439943",
            "registratiedatum": "2018-06-11",
            "startdatum": "2018-06-11",
        }

        url = reverse(zaak)

        response = self.client.put(url, body, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@tag("api_roles")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakDeleteRoleTests(JWTAuthMixin, TypeCheckMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_VERWIJDEREN]
    component = ComponentTypes.zrc
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.confidentieel

    def setUp(self):
        super().setUp()
        token = generate_jwt_auth(
            self.client_id,
            self.secret,
            user_id=self.user_id,
            user_representation=self.user_representation,
            roles=["role1"],
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype2 = ZaakTypeFactory.create(concept=False)
        super().setUpTestData()

        Autorisatie.objects.create(
            applicatie=cls.applicatie,
            component=cls.component,
            scopes=cls.scopes,
            zaaktype=cls.check_for_instance(cls.zaaktype2),
            max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
        )

    def test_zaak_delete(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_VERWIJDEREN],
            component=ComponentTypes.zrc,
        )

        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )

        url1 = reverse(zaak1)
        url2 = reverse(zaak2)
        url3 = reverse(zaak3)

        response1 = self.client.delete(url1, **ZAAK_WRITE_KWARGS)
        response2 = self.client.delete(url2, **ZAAK_WRITE_KWARGS)
        response3 = self.client.delete(url3, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response1.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_delete_permissions_cannot_exceed_application_zaaktypen(self):
        zaaktype3 = ZaakTypeFactory.create()
        zaaktype_url3 = f"http://testserver{reverse(zaaktype3)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url3,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak = ZaakFactory.create(
            zaaktype=zaaktype3,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        url = reverse(zaak)

        response = self.client.delete(url, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_delete_permissions_cannot_exceed_application_vertrouwelijkheidsaanduiding(
        self,
    ):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )

        url = reverse(zaak)

        response = self.client.delete(url, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_delete_permissions_cannot_exceed_application_scopes(self,):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )
        # Should not appear
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        self.autorisatie.scopes = []
        self.autorisatie.save()

        url = reverse(zaak)

        response = self.client.delete(url, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@tag("api_roles")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakZoekRoleTests(JWTAuthMixin, TypeCheckMixin, APITestCase):
    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]
    component = ComponentTypes.zrc
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.confidentieel

    def setUp(self):
        super().setUp()
        token = generate_jwt_auth(
            self.client_id,
            self.secret,
            user_id=self.user_id,
            user_representation=self.user_representation,
            roles=["role1"],
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype2 = ZaakTypeFactory.create(concept=False)
        super().setUpTestData()

        Autorisatie.objects.create(
            applicatie=cls.applicatie,
            component=cls.component,
            scopes=cls.scopes,
            zaaktype=cls.check_for_instance(cls.zaaktype2),
            max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
        )

    def test_zaak_zoek(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        # in district
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            zaakgeometrie=Point(4.887990, 52.377595),
        )  # LONG LAT
        #
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
            zaakgeometrie=Point(4.887990, 52.377595),
        )
        ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            zaakgeometrie=Point(4.887990, 52.377595),
        )

        url = get_operation_url("zaak__zoek")

        response = self.client.post(
            url,
            {
                "zaakgeometrie": {
                    "within": {
                        "type": "Polygon",
                        "coordinates": [POLYGON_AMSTERDAM_CENTRUM],
                    }
                }
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        detail_url = get_operation_url("zaak_read", uuid=zaak.uuid)
        self.assertEqual(response_data[0]["url"], f"http://testserver{detail_url}")

    def test_zaak_zoek_permissions_cannot_exceed_application_zaaktypen(self):
        zaaktype3 = ZaakTypeFactory.create()
        zaaktype_url3 = f"http://testserver{reverse(zaaktype3)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url3,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        ZaakFactory.create(
            zaaktype=zaaktype3,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            zaakgeometrie=Point(4.887990, 52.377595),
        )

        url = get_operation_url("zaak__zoek")

        response = self.client.post(
            url,
            {
                "zaakgeometrie": {
                    "within": {
                        "type": "Polygon",
                        "coordinates": [POLYGON_AMSTERDAM_CENTRUM],
                    }
                }
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 0)

    def test_zaak_zoek_permissions_cannot_exceed_application_vertrouwelijkheidsaanduiding(
        self,
    ):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )
        # Should not appear
        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            zaakgeometrie=Point(4.887990, 52.377595),
        )

        url = get_operation_url("zaak__zoek")

        response = self.client.post(
            url,
            {
                "zaakgeometrie": {
                    "within": {
                        "type": "Polygon",
                        "coordinates": [POLYGON_AMSTERDAM_CENTRUM],
                    }
                }
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 0)

    def test_zaak_zoek_permissions_cannot_exceed_application_scopes(self,):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
            zaakgeometrie=Point(4.887990, 52.377595),
        )
        self.autorisatie.scopes = []
        self.autorisatie.save()

        url = get_operation_url("zaak__zoek")

        response = self.client.post(
            url,
            {
                "zaakgeometrie": {
                    "within": {
                        "type": "Polygon",
                        "coordinates": [POLYGON_AMSTERDAM_CENTRUM],
                    }
                }
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 0)


@tag("api_roles")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakAuditTrailListRoleTests(JWTAuthMixin, TypeCheckMixin, APITestCase):
    scopes = [SCOPE_AUDITTRAILS_LEZEN]
    component = ComponentTypes.zrc
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.confidentieel

    def setUp(self):
        super().setUp()
        token = generate_jwt_auth(
            self.client_id,
            self.secret,
            user_id=self.user_id,
            user_representation=self.user_representation,
            roles=["role1"],
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype2 = ZaakTypeFactory.create(concept=False)
        super().setUpTestData()

        Autorisatie.objects.create(
            applicatie=cls.applicatie,
            component=cls.component,
            scopes=cls.scopes,
            zaaktype=cls.check_for_instance(cls.zaaktype2),
            max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
        )

    def test_zaak_audittrail_list(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_AUDITTRAILS_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )
        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url1 = reverse(zaak1)
        url2 = reverse(zaak2)
        url3 = reverse(zaak3)

        AuditTrail.objects.create(hoofd_object=url1, resource="Zaak", resultaat=200)
        AuditTrail.objects.create(hoofd_object=url2, resource="Zaak", resultaat=200)
        AuditTrail.objects.create(hoofd_object=url3, resource="Zaak", resultaat=200)

        audit_url1 = reverse("audittrail-list", kwargs={"zaak_uuid": zaak1.uuid},)
        audit_url2 = reverse("audittrail-list", kwargs={"zaak_uuid": zaak2.uuid},)
        audit_url3 = reverse("audittrail-list", kwargs={"zaak_uuid": zaak3.uuid},)

        response1 = self.client.get(audit_url1)
        response2 = self.client.get(audit_url2)
        response3 = self.client.get(audit_url3)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_audittrail_list_permissions_cannot_exceed_application_zaaktypen(self):
        zaaktype3 = ZaakTypeFactory.create()
        zaaktype_url3 = f"http://testserver{reverse(zaaktype3)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url3,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak = ZaakFactory.create(
            zaaktype=zaaktype3,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )
        url = reverse(zaak)

        AuditTrail.objects.create(hoofd_object=url, resource="Zaak", resultaat=200)

        audit_url = reverse("audittrail-list", kwargs={"zaak_uuid": zaak.uuid},)

        response = self.client.get(audit_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_audittrail_list_permissions_cannot_exceed_application_vertrouwelijkheidsaanduiding(
        self,
    ):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )
        url = reverse(zaak)

        AuditTrail.objects.create(hoofd_object=url, resource="Zaak", resultaat=200)

        audit_url = reverse("audittrail-list", kwargs={"zaak_uuid": zaak.uuid},)

        response = self.client.get(audit_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_audittrail_list_permissions_cannot_exceed_application_scopes(self,):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )
        # Should not appear
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url = reverse(zaak)

        self.autorisatie.scopes = []
        self.autorisatie.save()

        AuditTrail.objects.create(hoofd_object=url, resource="Zaak", resultaat=200)

        audit_url = reverse("audittrail-list", kwargs={"zaak_uuid": zaak.uuid},)

        response = self.client.get(audit_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@tag("api_roles")
@override_settings(ALLOWED_HOSTS=["testserver"])
class ZaakAuditTrailRetrieveRoleTests(JWTAuthMixin, TypeCheckMixin, APITestCase):
    scopes = [SCOPE_AUDITTRAILS_LEZEN]
    component = ComponentTypes.zrc
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduiding.confidentieel

    def setUp(self):
        super().setUp()
        token = generate_jwt_auth(
            self.client_id,
            self.secret,
            user_id=self.user_id,
            user_representation=self.user_representation,
            roles=["role1"],
        )
        self.client.credentials(HTTP_AUTHORIZATION=token)

    @classmethod
    def setUpTestData(cls):
        cls.zaaktype = ZaakTypeFactory.create(concept=False)
        cls.zaaktype2 = ZaakTypeFactory.create(concept=False)
        super().setUpTestData()

        Autorisatie.objects.create(
            applicatie=cls.applicatie,
            component=cls.component,
            scopes=cls.scopes,
            zaaktype=cls.check_for_instance(cls.zaaktype2),
            max_vertrouwelijkheidaanduiding=cls.max_vertrouwelijkheidaanduiding,
        )

    def test_zaak_audittrail_retrieve(self):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"

        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_AUDITTRAILS_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak1 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        zaak2 = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )
        zaak3 = ZaakFactory.create(
            zaaktype=self.zaaktype2,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url1 = reverse(zaak1)
        url2 = reverse(zaak2)
        url3 = reverse(zaak3)

        audittrail1 = AuditTrail.objects.create(
            hoofd_object=url1, resource="Zaak", resultaat=200
        )
        audittrail2 = AuditTrail.objects.create(
            hoofd_object=url2, resource="Zaak", resultaat=200
        )
        audittrail3 = AuditTrail.objects.create(
            hoofd_object=url3, resource="Zaak", resultaat=200
        )

        audit_url1 = reverse(
            "audittrail-detail",
            kwargs={"zaak_uuid": zaak1.uuid, "uuid": audittrail1.uuid},
        )
        audit_url2 = reverse(
            "audittrail-detail",
            kwargs={"zaak_uuid": zaak2.uuid, "uuid": audittrail2.uuid},
        )
        audit_url3 = reverse(
            "audittrail-detail",
            kwargs={"zaak_uuid": zaak3.uuid, "uuid": audittrail3.uuid},
        )

        response1 = self.client.get(audit_url1)
        response2 = self.client.get(audit_url2)
        response3 = self.client.get(audit_url3)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_audittrail_retrieve_permissions_cannot_exceed_application_zaaktypen(
        self,
    ):
        zaaktype3 = ZaakTypeFactory.create()
        zaaktype_url3 = f"http://testserver{reverse(zaaktype3)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url3,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak = ZaakFactory.create(
            zaaktype=zaaktype3,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.vertrouwelijk,
        )

        url = reverse(zaak)

        audittrail = AuditTrail.objects.create(
            hoofd_object=url, resource="Zaak", resultaat=200
        )

        audit_url = reverse(
            "audittrail-detail",
            kwargs={"zaak_uuid": zaak.uuid, "uuid": audittrail.uuid},
        )

        response = self.client.get(audit_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_audittrail_retrieve_permissions_cannot_exceed_application_vertrouwelijkheidsaanduiding(
        self,
    ):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )

        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.zeer_geheim,
        )

        url = reverse(zaak)

        audittrail = AuditTrail.objects.create(
            hoofd_object=url, resource="Zaak", resultaat=200
        )

        audit_url = reverse(
            "audittrail-detail",
            kwargs={"zaak_uuid": zaak.uuid, "uuid": audittrail.uuid},
        )

        response = self.client.get(audit_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_zaak_audittrail_retrieve_permissions_cannot_exceed_application_scopes(
        self,
    ):
        zaaktype_url = f"http://testserver{reverse(self.zaaktype)}"
        RoleFactory.create(
            name="Role 1",
            slug="role1",
            zaaktype=zaaktype_url,
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
            scopes=[SCOPE_ZAKEN_ALLES_LEZEN],
            component=ComponentTypes.zrc,
        )
        zaak = ZaakFactory.create(
            zaaktype=self.zaaktype,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        url = reverse(zaak)

        audittrail = AuditTrail.objects.create(
            hoofd_object=url, resource="Zaak", resultaat=200
        )

        audit_url = reverse(
            "audittrail-detail",
            kwargs={"zaak_uuid": zaak.uuid, "uuid": audittrail.uuid},
        )

        response = self.client.get(audit_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
