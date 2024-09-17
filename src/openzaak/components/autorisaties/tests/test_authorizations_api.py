# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.test import override_settings, tag

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.models import JWTSecret
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.autorisaties.models import CatalogusAutorisatie
from openzaak.components.besluiten.api.scopes import (
    SCOPE_BESLUITEN_AANMAKEN,
    SCOPE_BESLUITEN_BIJWERKEN,
)
from openzaak.components.catalogi.tests.factories import (
    BesluitTypeFactory,
    CatalogusFactory,
    InformatieObjectTypeFactory,
    ZaakTypeFactory,
)
from openzaak.components.documenten.api.scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
)
from openzaak.components.zaken.api.scopes import (
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
)
from openzaak.tests.utils import JWTAuthMixin

from ..api.scopes import SCOPE_AUTORISATIES_BIJWERKEN, SCOPE_AUTORISATIES_LEZEN
from ..api.validators import UniqueClientIDValidator
from .factories import (
    ApplicatieFactory,
    AutorisatieFactory,
    CatalogusAutorisatieFactory,
)
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
                    "scopes": ["zaken.lezen", "zaken.aanmaken"],
                    "zaaktype": "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/1/zaaktypen/1",
                    "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                },
                {
                    "component": ComponentTypes.zrc,
                    "scopes": [
                        "zaken.lezen",
                        "zaken.aanmaken",
                        "zaken.verwijderen",
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
        self.assertEqual(auth1.scopes, ["zaken.lezen", "zaken.aanmaken"])
        self.assertEqual(
            auth1.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        self.assertEqual(auth2.applicatie, applicatie)
        self.assertEqual(auth2.component, ComponentTypes.zrc)
        self.assertEqual(
            auth2.scopes,
            [
                "zaken.lezen",
                "zaken.aanmaken",
                "zaken.verwijderen",
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
                    "scopes": ["zaken.lezen", "zaken.aanmaken"],
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
                    "scopes": ["zaken.lezen", "zaken.aanmaken"],
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

    def test_create_with_empty_scopes(self):
        """
        Assert that an autorisatie with empty scopes can be created.

        The API spec does not specify a minimum number of elements, which means that
        an empty list is permitted.

        This is regression found during upgrading the dependencies, which caused the
        Postman collection to fail.
        """
        url = get_operation_url("applicatie_create")

        data = {
            "client_ids": ["id1"],
            "label": "some-app",
            "autorisaties": [
                {
                    "component": ComponentTypes.zrc,
                    "scopes": [],
                    "zaaktype": "https://catalogi-api.vng.cloud/api/v1/catalogus/1/zaaktypen/1",
                    "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                }
            ],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ReadAuthorizationsTests(JWTAuthMixin, APITestCase):
    scopes = [str(SCOPE_AUTORISATIES_LEZEN)]
    component = ComponentTypes.ac

    maxDiff = None

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
        app = ApplicatieFactory.create(
            client_ids=["client id"], heeft_alle_autorisaties=True
        )

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

    def test_non_compliant_applications_not_in_api(self):
        """
        Assert that applications that aren't superuser and have no authorizations don't
        show up in the API.

        Regression test for #835 -- it's possible to create an application without
        ``heeft_alle_autorisaties`` set to True and without any authorizations via the
        admin interface (since configuration authorizations is a multi-step process).
        These applications may not show up in the API responses, because they break
        expectations from what the standard allows.
        """
        app = ApplicatieFactory.create(heeft_alle_autorisaties=False)
        url = reverse(Applicatie)
        app_url = f"http://testserver{reverse(app)}"

        with self.subTest(case="list"):
            response = self.client.get(url)

            app_urls = [app["url"] for app in response.json()["results"]]
            self.assertNotIn(app_url, app_urls)

        with self.subTest(case="detail"):
            response = self.client.get(app_url)

            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        app.heeft_alle_autorisaties = True
        app.save()
        CatalogusAutorisatieFactory.create(applicatie=app, component=ComponentTypes.brc)

        with self.subTest(case="list"):
            response = self.client.get(url)

            app_urls = [app["url"] for app in response.json()["results"]]
            self.assertNotIn(app_url, app_urls)

        with self.subTest(case="detail"):
            response = self.client.get(app_url)

            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @tag("gh-1661")
    def test_fetch_applicatie_with_catalogus_autorisaties_and_regular_autorisaties(
        self,
    ):
        """
        Test if CatalogusAutorisaties are displayed as separate autorisaties for each
        zaak/besluit/informatieobjecttype when retrieving the Applicatie via the API
        """
        app = ApplicatieFactory.create(
            client_ids=["client id"], heeft_alle_autorisaties=False
        )

        zaaktype_regular_autorisatie = ZaakTypeFactory.create()
        # Create a "regular" autorisatie, this should be shown first in the list
        AutorisatieFactory.create(
            applicatie=app,
            zaaktype=f"http://testserver{reverse(zaaktype_regular_autorisatie)}",
            component=ComponentTypes.zrc,
            scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url = get_operation_url("applicatie_read", uuid=app.uuid)

        catalogus1, catalogus2 = CatalogusFactory.create_batch(2)
        zaaktype1, zaaktype2 = ZaakTypeFactory.create_batch(2, catalogus=catalogus1)
        zaaktype3, zaaktype4 = ZaakTypeFactory.create_batch(2, catalogus=catalogus2)

        besluittype1, besluittype2 = BesluitTypeFactory.create_batch(
            2,
            catalogus=catalogus1,
            zaaktypen=[zaaktype1],
        )
        besluittype3, besluittype4 = BesluitTypeFactory.create_batch(
            2,
            catalogus=catalogus2,
            zaaktypen=[zaaktype3],
        )

        iotype1, iotype2 = InformatieObjectTypeFactory.create_batch(
            2,
            catalogus=catalogus1,
            zaaktypen=[zaaktype1],
        )
        iotype3, iotype4 = InformatieObjectTypeFactory.create_batch(
            2,
            catalogus=catalogus2,
            zaaktypen=[zaaktype4],
        )

        CatalogusAutorisatieFactory.create(
            applicatie=app,
            catalogus=catalogus1,
            component=ComponentTypes.zrc,
            scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )
        CatalogusAutorisatieFactory.create(
            applicatie=app,
            catalogus=catalogus2,
            component=ComponentTypes.brc,
            scopes=[SCOPE_BESLUITEN_AANMAKEN, SCOPE_BESLUITEN_BIJWERKEN],
        )
        CatalogusAutorisatieFactory.create(
            applicatie=app,
            catalogus=catalogus1,
            component=ComponentTypes.drc,
            scopes=[SCOPE_DOCUMENTEN_AANMAKEN, SCOPE_DOCUMENTEN_BIJWERKEN],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["url"], f"http://testserver{reverse(app)}")

        expected = [
            {
                "component": ComponentTypes.zrc,
                "component_weergave": "Zaken API",
                "scopes": [str(SCOPE_ZAKEN_CREATE), str(SCOPE_ZAKEN_BIJWERKEN)],
                "zaaktype": f"http://testserver{reverse(zaaktype_regular_autorisatie)}",
                "max_vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            },
            {
                "component": ComponentTypes.brc,
                "component_weergave": "Besluiten API",
                "scopes": [
                    str(SCOPE_BESLUITEN_AANMAKEN),
                    str(SCOPE_BESLUITEN_BIJWERKEN),
                ],
                "besluittype": f"http://testserver{reverse(besluittype4)}",
            },
            {
                "component": ComponentTypes.brc,
                "component_weergave": "Besluiten API",
                "scopes": [
                    str(SCOPE_BESLUITEN_AANMAKEN),
                    str(SCOPE_BESLUITEN_BIJWERKEN),
                ],
                "besluittype": f"http://testserver{reverse(besluittype3)}",
            },
            {
                "component": ComponentTypes.drc,
                "component_weergave": "Documenten API",
                "scopes": [
                    str(SCOPE_DOCUMENTEN_AANMAKEN),
                    str(SCOPE_DOCUMENTEN_BIJWERKEN),
                ],
                "informatieobjecttype": f"http://testserver{reverse(iotype2)}",
                "max_vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            },
            {
                "component": ComponentTypes.drc,
                "component_weergave": "Documenten API",
                "scopes": [
                    str(SCOPE_DOCUMENTEN_AANMAKEN),
                    str(SCOPE_DOCUMENTEN_BIJWERKEN),
                ],
                "informatieobjecttype": f"http://testserver{reverse(iotype1)}",
                "max_vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            },
            {
                "component": ComponentTypes.zrc,
                "component_weergave": "Zaken API",
                "scopes": [str(SCOPE_ZAKEN_CREATE), str(SCOPE_ZAKEN_BIJWERKEN)],
                "zaaktype": f"http://testserver{reverse(zaaktype2)}",
                "max_vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.confidentieel,
            },
            {
                "component": ComponentTypes.zrc,
                "component_weergave": "Zaken API",
                "scopes": [str(SCOPE_ZAKEN_CREATE), str(SCOPE_ZAKEN_BIJWERKEN)],
                "zaaktype": f"http://testserver{reverse(zaaktype1)}",
                "max_vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.confidentieel,
            },
        ]

        self.assertEqual(response.data["autorisaties"], expected)

    @tag("gh-1661")
    def test_fetch_applicatie_with_only_catalogus_autorisaties(self):
        """
        Test if Applicaties that have no "regular" Autorisaties associated with them
        can be retrieved
        """
        app = ApplicatieFactory.create(
            client_ids=["client id"], heeft_alle_autorisaties=False
        )

        url = get_operation_url("applicatie_read", uuid=app.uuid)

        catalogus = CatalogusFactory.create()
        zaaktype = ZaakTypeFactory.create(catalogus=catalogus)

        CatalogusAutorisatieFactory.create(
            applicatie=app,
            catalogus=catalogus,
            component=ComponentTypes.zrc,
            scopes=[SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.confidentieel,
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["url"], f"http://testserver{reverse(app)}")

        expected = [
            {
                "component": ComponentTypes.zrc,
                "component_weergave": "Zaken API",
                "scopes": [str(SCOPE_ZAKEN_CREATE), str(SCOPE_ZAKEN_BIJWERKEN)],
                "zaaktype": f"http://testserver{reverse(zaaktype)}",
                "max_vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.confidentieel,
            },
        ]

        self.assertEqual(response.data["autorisaties"], expected)

    def test_list_with_page_size_in_query(self):
        AutorisatieFactory.create_batch(
            10,
            applicatie__client_ids=["id3"],
            component=ComponentTypes.zrc,
            scopes=["dummy.scope"],
            zaaktype="https://example.com",
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        url = get_operation_url("applicatie_list")
        response = self.client.get(url, {"clientIds": "id3", "pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"], f"http://testserver{url}?clientIds=id3&page=2&pageSize=5"
        )


class UpdateAuthorizationsTests(JWTAuthMixin, APITestCase):
    scopes = [str(SCOPE_AUTORISATIES_BIJWERKEN)]
    component = ComponentTypes.ac

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.zaaktype = ZaakTypeFactory.create()

        autorisatie = AutorisatieFactory.create(
            applicatie__client_ids=["id1", "id2"],
            component=ComponentTypes.zrc,
            scopes=["dummy.scope"],
            zaaktype=f"http://testserver{reverse(cls.zaaktype)}",
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
                    "scopes": ["zaken.lezen", "zaken.aanmaken"],
                    "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                    "zaaktype": "https://ref.tst.vng.cloud/zrc/api/v1/catalogus/1/zaaktypen/1",
                },
                {
                    "component": ComponentTypes.zrc,
                    "scopes": [
                        "zaken.lezen",
                        "zaken.aanmaken",
                        "zaken.verwijderen",
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

    @tag("gh-1661")
    @override_settings(ALLOWED_HOSTS=["testserver.com"])
    def test_update_authorization_deletes_existing_catalogus_autorisatie(self):
        """
        Updating an Applicatie with autorisaties for typen from another
        """
        zaaktype = ZaakTypeFactory.create()
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            catalogus=CatalogusFactory.create(),
            component=ComponentTypes.zrc,
            scopes=["dummy.scope"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        CatalogusAutorisatieFactory.create(
            applicatie=self.applicatie,
            catalogus=CatalogusFactory.create(),
            component=ComponentTypes.zrc,
            scopes=["dummy.scope"],
            max_vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        url = get_operation_url("applicatie_partial_update", uuid=self.applicatie.uuid)

        response = self.client.patch(
            url,
            {
                "autorisaties": [
                    {
                        "component": ComponentTypes.zrc,
                        "scopes": ["dummy.scope"],
                        "maxVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.beperkt_openbaar,
                        # Zaaktype is part of the same catalogus as the CatalogusAutorisatie
                        "zaaktype": f"http://testserver.com{reverse(zaaktype)}",
                    },
                ]
            },
            headers={"host": "testserver.com"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # The existing CatalogusAutorisaties should be deleted
        self.assertFalse(CatalogusAutorisatie.objects.exists())

        # The new Autorisatie should be created
        [autorisatie] = self.applicatie.autorisaties.all()

        self.assertEqual(autorisatie.component, ComponentTypes.zrc)
        self.assertEqual(autorisatie.scopes, ["dummy.scope"])
        self.assertEqual(
            autorisatie.max_vertrouwelijkheidaanduiding,
            VertrouwelijkheidsAanduiding.beperkt_openbaar,
        )
        self.assertEqual(
            autorisatie.zaaktype, f"http://testserver.com{reverse(zaaktype)}"
        )
