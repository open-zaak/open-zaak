# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.models import JWTSecret
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.utils.tests import JWTAuthMixin

from ..api.scopes import SCOPE_AUTORISATIES_BIJWERKEN, SCOPE_AUTORISATIES_LEZEN
from ..api.validators import UniqueClientIDValidator
from .factories import ApplicatieFactory, AutorisatieFactory
from .utils import get_operation_url


class SetAuthorizationsTests(JWTAuthMixin, APITestCase):
    scopes = [str(SCOPE_AUTORISATIES_BIJWERKEN)]
    component = ComponentTypes.ac

    def test_create_application_with_all_permissions(self):
        """
        Test registration of an application with all authorizations.

        All authorizations should be granted because of the flag provided. This
        gives an option to do coarse-grained authorization for an application.
        """
        url = get_operation_url("applicatie_create")

        data = {
            "client_ids": ["id1", "id2"],
            "label": "Melding Openbare Ruimte consumer",
            "heeftAlleAutorisaties": True,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        applicatie = Applicatie.objects.get(client_ids=["id1", "id2"])

        self.assertEqual(applicatie.client_ids, ["id1", "id2"])
        self.assertEqual(applicatie.label, "Melding Openbare Ruimte consumer")
        self.assertEqual(applicatie.heeft_alle_autorisaties, True)

    def test_create_application_with_detail_permissions(self):
        """
        Test registration of an application with limited authorizations.

        Fine-grained authorization can be achieved per ZaakType, which limits
        which scopes are allowed for this particular type. The same applies
        for maxVetrouwelijkheidaanduiding.
        """
        url = get_operation_url("applicatie_create")

        data = {
            "client_ids": ["id1", "id2"],
            "label": "Melding Openbare Ruimte consumer",
            "autorisaties": [
                {
                    "component": ComponentTypes.zrc,
                    "scopes": ["zds.scopes.zaken.lezen", "zds.scopes.zaken.aanmaken"],
                    "zaaktype": "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/1/zaaktypen/1",
                    "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                },
                {
                    "component": ComponentTypes.zrc,
                    "scopes": [
                        "zds.scopes.zaken.lezen",
                        "zds.scopes.zaken.aanmaken",
                        "zds.scopes.zaken.verwijderen",
                    ],
                    "zaaktype": "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/2/zaaktypen/1",
                    "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.zeer_geheim,
                },
            ],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        applicatie = Applicatie.objects.get(client_ids=["id1", "id2"])
        autorisaties = (
            Autorisatie.objects.filter(applicatie=applicatie).order_by("zaaktype").all()
        )

        self.assertEqual(applicatie.client_ids, ["id1", "id2"])
        self.assertEqual(applicatie.label, "Melding Openbare Ruimte consumer")
        self.assertEqual(applicatie.heeft_alle_autorisaties, False)
        self.assertEqual(len(autorisaties), 2)

        auth1, auth2 = autorisaties

        self.assertEqual(auth1.applicatie, applicatie)
        self.assertEqual(auth1.component, ComponentTypes.zrc)
        self.assertEqual(
            auth1.zaaktype,
            "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/1/zaaktypen/1",
        )
        self.assertEqual(
            auth1.scopes, ["zds.scopes.zaken.lezen", "zds.scopes.zaken.aanmaken"]
        )
        self.assertEqual(
            auth1.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        self.assertEqual(auth2.applicatie, applicatie)
        self.assertEqual(auth2.component, ComponentTypes.zrc)
        self.assertEqual(
            auth2.scopes,
            [
                "zds.scopes.zaken.lezen",
                "zds.scopes.zaken.aanmaken",
                "zds.scopes.zaken.verwijderen",
            ],
        )
        self.assertEqual(
            auth2.zaaktype,
            "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/2/zaaktypen/1",
        )
        self.assertEqual(
            auth2.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.zeer_geheim,
        )

    def test_create_all_permissions_and_explicitly_provided(self):
        """
        Assert that you either specify heeftAlleAutorisatie or autorisaties.

        Part one of the XOR test.
        """
        url = get_operation_url("applicatie_create")

        data = {
            "client_ids": ["id1", "id2"],
            "label": "Melding Openbare Ruimte consumer",
            "heeftAlleAutorisaties": True,
            "autorisaties": [
                {
                    "component": ComponentTypes.zrc,
                    "scopes": ["zds.scopes.zaken.lezen", "zds.scopes.zaken.aanmaken"],
                    "zaaktype": "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/1/zaaktypen/1",
                    "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                }
            ],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "ambiguous-authorizations-specified")

    def test_create_no_permissions_provided(self):
        """
        Assert that you either specify heeftAlleAutorisatie or autorisaties.

        Part two of the XOR test.
        """
        url = get_operation_url("applicatie_create")

        data = {
            "client_ids": ["id1", "id2"],
            "label": "Melding Openbare Ruimte consumer",
            "autorisaties": [],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "missing-authorizations")

    def test_create_no_permissions_provided_2(self):
        """
        Assert that you either specify heeftAlleAutorisatie or autorisaties.

        Part three of the XOR test.
        """
        url = get_operation_url("applicatie_create")

        data = {
            "client_ids": ["id1", "id2"],
            "label": "Melding Openbare Ruimte consumer",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "missing-authorizations")

    def test_create_application_with_null_autorisaties(self):
        """
        Test request with autorisaties = null
        """
        url = get_operation_url("applicatie_create")

        data = {
            "client_ids": ["id1", "id2"],
            "label": "Melding Openbare Ruimte consumer",
            "heeftAlleAutorisaties": True,
            "autorisaties": None,
        }

        response = self.client.post(url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "autorisaties")
        self.assertEqual(error["code"], "null")

    def test_create_application_with_null_heeft_alle_autorisaties(self):
        """
        Test request with heeftAlleAutorisaties = null
        """
        url = get_operation_url("applicatie_create")

        data = {
            "client_ids": ["id1", "id2"],
            "label": "Melding Openbare Ruimte consumer",
            "heeftAlleAutorisaties": None,
            "autorisaties": [
                {
                    "component": ComponentTypes.zrc,
                    "scopes": ["zds.scopes.zaken.lezen", "zds.scopes.zaken.aanmaken"],
                    "zaaktype": "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/1/zaaktypen/1",
                    "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                }
            ],
        }

        response = self.client.post(url, data)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "heeftAlleAutorisaties")
        self.assertEqual(error["code"], "null")

    def test_create_duplicate_client_id(self):
        """
        Assert that a client ID can occur only once.

        A client ID belongs to one application. When trying to create another
        application with a client ID that already exists, the API should
        throw a validation error.
        """
        url = get_operation_url("applicatie_create")
        ApplicatieFactory.create(client_ids=["client1", "client2"])
        data = {
            "clientIds": ["client2"],
            "label": "Faulty application",
            "autorisaties": [
                {"component": ComponentTypes.ac, "scopes": ["autorisaties.lezen"]}
            ],
        }

        response = self.client.post(url, data)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "clientIds")
        self.assertEqual(error["code"], UniqueClientIDValidator.code)

    def test_create_with_client_id_not_in_jwtsecret(self):
        """
        Test the creation of JWTSecret missing object
        """
        url = get_operation_url("applicatie_create")
        JWTSecret.objects.create(identifier="id1", secret="secret1")
        data = {
            "client_ids": ["id1", "id2"],
            "label": "Melding Openbare Ruimte consumer",
            "heeftAlleAutorisaties": True,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(JWTSecret.objects.filter(identifier="id2").exists(), True)

        credential = JWTSecret.objects.get(identifier="id2")

        self.assertEqual(credential.secret, "")


class ReadAuthorizationsTests(JWTAuthMixin, APITestCase):
    scopes = [str(SCOPE_AUTORISATIES_LEZEN)]
    component = ComponentTypes.ac

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        AutorisatieFactory.create(
            applicatie__client_ids=["id1", "id2"],
            component=ComponentTypes.zrc,
            scopes=["dummy.scope"],
            zaaktype="https://example.com",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

    def test_filter_client_id_hit(self):
        url = get_operation_url("applicatie_list")

        response = self.client.get(url, {"clientIds": "id2"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filter_client_id_miss(self):
        url = get_operation_url("applicatie_list")

        response = self.client.get(url, {"clientIds": "id3"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_fetch_via_client_id(self):
        """
        Retrieve THE application object, using a client ID as lookup.
        """
        url = get_operation_url("applicatie_consumer")
        app = ApplicatieFactory.create(client_ids=["client id"])

        response = self.client.get(url, {"clientId": "client id"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["url"], f"http://testserver{reverse(app)}")

    def test_validate_unknown_query_params(self):
        ApplicatieFactory.create_batch(2)
        url = reverse(Applicatie)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")


class UpdateAuthorizationsTests(JWTAuthMixin, APITestCase):
    scopes = [str(SCOPE_AUTORISATIES_BIJWERKEN)]
    component = ComponentTypes.ac

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        autorisatie = AutorisatieFactory.create(
            applicatie__client_ids=["id1", "id2"],
            component=ComponentTypes.zrc,
            scopes=["dummy.scope"],
            zaaktype="https://example.com",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        cls.applicatie = autorisatie.applicatie

    def test_update_client_ids(self):
        url = get_operation_url("applicatie_partial_update", uuid=self.applicatie.uuid)

        response = self.client.patch(url, {"client_ids": ["id1"]})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.applicatie.refresh_from_db()
        self.assertEqual(self.applicatie.client_ids, ["id1"])

    def test_replace_authorizations(self):
        url = get_operation_url("applicatie_partial_update", uuid=self.applicatie.uuid)
        data = {
            "autorisaties": [
                {
                    "component": ComponentTypes.zrc,
                    "scopes": ["zds.scopes.zaken.lezen", "zds.scopes.zaken.aanmaken"],
                    "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                    "zaaktype": "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/1/zaaktypen/1",
                },
                {
                    "component": ComponentTypes.zrc,
                    "scopes": [
                        "zds.scopes.zaken.lezen",
                        "zds.scopes.zaken.aanmaken",
                        "zds.scopes.zaken.verwijderen",
                    ],
                    "zaaktype": "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/2/zaaktypen/1",
                    "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.zeer_geheim,
                },
            ]
        }

        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.applicatie.autorisaties.count(), 2)

        auth1, auth2 = self.applicatie.autorisaties.order_by("zaaktype").all()

        self.assertEqual(
            auth1.zaaktype,
            "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/1/zaaktypen/1",
        )
        self.assertEqual(
            auth1.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        self.assertEqual(
            auth2.zaaktype,
            "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/2/zaaktypen/1",
        )
        self.assertEqual(
            auth2.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.zeer_geheim,
        )

    def test_update_authorization_incorrect(self):
        url = get_operation_url("applicatie_partial_update", uuid=self.applicatie.uuid)

        response = self.client.patch(url, {"heeftAlleAutorisaties": True})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "ambiguous-authorizations-specified")

    def test_update_with_client_id_not_in_jwtsecret(self):
        """
        Test the creation of JWTSecret missing object
        """
        self.applicatie.client_ids = ["id1"]
        self.applicatie.save()

        url = get_operation_url("applicatie_partial_update", uuid=self.applicatie.uuid)
        JWTSecret.objects.create(identifier="id1", secret="secret1")
        data = {"client_ids": ["id1", "id2"]}

        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(JWTSecret.objects.filter(identifier="id2").exists(), True)

        credential = JWTSecret.objects.get(identifier="id2")

        self.assertEqual(credential.secret, "")
