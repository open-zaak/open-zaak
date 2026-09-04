# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact


from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.audittrails.models import AuditTrail
from vng_api_common.tests import get_validation_errors

from openzaak.components.besluiten.api.audits import AUDIT_BRC
from openzaak.components.besluiten.models import Besluit, BesluitInformatieObject
from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)
from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.components.zaken.tests.factories import ZaakFactory
from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.urls import reverse


class BesluitenApiDeprecationTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()
        self.besluit = BesluitFactory.create(for_zaak=True)
        self.besluitInformatieObject = BesluitInformatieObjectFactory.create()

    def test_deprecated_besluiten_api_response(self):
        with self.subTest("besluit"):
            url = reverse(self.besluit, namespace="besluiten")

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("besluiten/api/v1/besluiten", response.data["url"])
            self.assertIn("catalogi/api/v1/besluittypen", response.data["besluittype"])
            self.assertIn("zaken/api/v1/zaken", response.data["zaak"])

        with self.subTest("besluitinformatieobject"):
            url = reverse(self.besluitInformatieObject, namespace="besluiten")

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn(
                "besluiten/api/v1/besluitinformatieobjecten", response.data["url"]
            )
            self.assertIn("besluiten/api/v1/besluiten", response.data["besluit"])
            self.assertIn(
                "documenten/api/v1/enkelvoudiginformatieobjecten",
                response.data["informatieobject"],
            )

    def test_zaken_api_response(self):
        with self.subTest("besluit"):
            url = reverse(self.besluit, namespace="zaken")

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("zaken/api/v1/besluiten", response.data["url"])
            self.assertIn("catalogi/api/v1/besluittypen", response.data["besluittype"])
            self.assertIn("zaken/api/v1/zaken", response.data["zaak"])

        with self.subTest("besluitinformatieobject"):
            url = reverse(self.besluitInformatieObject, namespace="zaken")

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn(
                "zaken/api/v1/besluitinformatieobjecten", response.data["url"]
            )
            self.assertIn("zaken/api/v1/besluiten", response.data["besluit"])
            self.assertIn(
                "documenten/api/v1/enkelvoudiginformatieobjecten",
                response.data["informatieobject"],
            )

    def test_deprecated_paths(self):
        self.assertEqual(
            reverse("besluiten:besluit-list"), "/besluiten/api/v1/besluiten"
        )
        self.assertEqual(
            reverse("besluiten:besluit-detail", kwargs={"uuid": 1}),
            "/besluiten/api/v1/besluiten/1",
        )
        self.assertEqual(
            reverse("besluiten:besluitinformatieobject-list"),
            "/besluiten/api/v1/besluitinformatieobjecten",
        )
        self.assertEqual(
            reverse("besluiten:besluitinformatieobject-detail", kwargs={"uuid": 1}),
            "/besluiten/api/v1/besluitinformatieobjecten/1",
        )
        self.assertEqual(
            reverse("besluiten:verwerkbesluit-list"),
            "/besluiten/api/v1/besluit_verwerken",
        )
        self.assertEqual(
            reverse("besluiten:audittrail-list", kwargs={"besluit_uuid": 1}),
            "/besluiten/api/v1/besluiten/1/audittrail",
        )

    def test_new_paths(self):
        self.assertEqual(reverse("zaken:besluit-list"), "/zaken/api/v1/besluiten")
        self.assertEqual(
            reverse("zaken:besluit-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/besluiten/1",
        )
        self.assertEqual(
            reverse("zaken:besluitinformatieobject-list"),
            "/zaken/api/v1/besluitinformatieobjecten",
        )
        self.assertEqual(
            reverse("zaken:besluitinformatieobject-detail", kwargs={"uuid": 1}),
            "/zaken/api/v1/besluitinformatieobjecten/1",
        )
        self.assertEqual(
            reverse("zaken:verwerkbesluit-list"), "/zaken/api/v1/besluit_verwerken"
        )

        # audittrails
        self.assertEqual(
            reverse("zaken:audittrail-list", kwargs={"besluit_uuid": 1}),
            "/zaken/api/v1/besluiten/1/audittrail",
        )
        self.assertEqual(
            reverse("zaken:audittrail-list", kwargs={"zaak_uuid": 1}),
            "/zaken/api/v1/zaken/1/audittrail",
        )

    def test_create_bio_in_besluiten_with_zaken_url(self):
        url = reverse(BesluitInformatieObject, namespace="besluiten")

        besluit = BesluitFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio.informatieobjecttype.besluittypen.add(besluit.besluittype)

        response = self.client.post(
            url,
            {
                "besluit": f"http://testserver{reverse(besluit, namespace='zaken')}",
                "informatieobject": f"http://testserver{reverse(eio)}",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_bio_in_zaken_with_besluiten_url(self):
        url = reverse(BesluitInformatieObject, namespace="zaken")

        besluit = BesluitFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio.informatieobjecttype.besluittypen.add(besluit.besluittype)

        response = self.client.post(
            url,
            {
                "besluit": f"http://testserver{reverse(besluit, namespace='besluiten')}"
                "",
                "informatieobject": f"http://testserver{reverse(eio)}",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_bio_in_zaken_with_non_existent_namespace(self):
        """
        resolve_path in permission check returns ObjectNotFound
        """
        url = reverse(BesluitInformatieObject, namespace="zaken")

        besluit = BesluitFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio.informatieobjecttype.besluittypen.add(besluit.besluittype)

        response = self.client.post(
            url,
            {
                "besluit": f"http://testserver/blabla/api/v1/besluiten/{besluit.uuid}",
                "informatieobject": f"http://testserver{reverse(eio)}",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "besluit")
        self.assertEqual(error["code"], "object-does-not-exist")

    def test_create_zaakbesluit(self):
        zaak = ZaakFactory.create()
        besluit = BesluitFactory.create(zaak=zaak)
        besluit.besluittype.zaaktypen.add(zaak.zaaktype)

        with self.subTest("both in zaken namespace"):
            url = f"{reverse(zaak, namespace='zaken')}/besluiten"
            response = self.client.post(
                url,
                {
                    "besluit": f"http://testserver{reverse(besluit, namespace='zaken')}",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        with self.subTest("besluit namespace"):
            url = f"{reverse(zaak, namespace='zaken')}/besluiten"
            response = self.client.post(
                url,
                {
                    "besluit": f"http://testserver{reverse(besluit, namespace='besluiten')}",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        with self.subTest("non existent namespace"):
            url = f"{reverse(zaak, namespace='zaken')}/besluiten"
            response = self.client.post(
                url,
                {
                    "besluit": f"http://testserver/blabla/api/v1/besluiten/{besluit.uuid}",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BesluitAudittrailTests(JWTAuthMixin, APITestCase):
    """
    Urls are stored in auditrail itself and won't change when changing namespace
    """

    heeft_alle_autorisaties = True
    maxDiff = None

    def setUp(self):
        super().setUp()

        besluittype = BesluitTypeFactory.create(concept=False)
        self.besluittype_url = f"http://testserver{reverse(besluittype)}"
        self.data = {
            "besluittype": self.besluittype_url,
            "verantwoordelijke_organisatie": "517439943",
            "datum": "2026-05-05",
            "ingangsdatum": "2026-05-05",
            "toelichting": "desc",
        }

    def test_audittrail_in_besluiten_api(self):
        besluiten_url = reverse("besluiten:besluit-list")

        response = self.client.post(besluiten_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        audittrail = AuditTrail.objects.get()
        besluit = Besluit.objects.get()
        besluit_url = reverse(besluit)

        with self.subTest("audittrail model"):
            self.assertEqual(audittrail.bron, AUDIT_BRC.component_name)
            self.assertEqual(audittrail.actie, "create")
            self.assertEqual(audittrail.resultaat, 201)
            self.assertEqual(audittrail.hoofd_object, f"http://testserver{besluit_url}")
            self.assertEqual(audittrail.resource, "besluit")
            self.assertEqual(audittrail.resource_url, f"http://testserver{besluit_url}")
            self.assertEqual(
                audittrail.resource_weergave, besluit.unique_representation()
            )

        with self.subTest("fetch from besluiten api"):
            url = reverse(
                "besluiten:audittrail-list", kwargs={"besluit_uuid": besluit.uuid}
            )

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()[0]

            self.assertEqual(data["bron"], AUDIT_BRC.component_name)
            self.assertEqual(data["hoofdObject"], f"http://testserver{besluit_url}")
            self.assertEqual(data["resourceUrl"], f"http://testserver{besluit_url}")
            self.assertEqual(
                data["wijzigingen"],
                {
                    "oud": None,
                    "nieuw": {
                        "url": f"http://testserver{besluit_url}",
                        "zaak": "",
                        "datum": "2026-05-05",
                        "besluittype": self.besluittype_url,
                        "toelichting": "desc",
                        "vervaldatum": None,
                        "vervalreden": "",
                        "ingangsdatum": "2026-05-05",
                        "verzenddatum": None,
                        "identificatie": "BESLUIT-2026-0000000001",
                        "bestuursorgaan": "",
                        "publicatiedatum": None,
                        "vervalredenWeergave": "",
                        "uiterlijkeReactiedatum": None,
                        "verantwoordelijkeOrganisatie": "517439943",
                    },
                },
            )

        with self.subTest("fetch from zaken api"):
            url = reverse(
                "zaken:audittrail-list", kwargs={"besluit_uuid": besluit.uuid}
            )

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()[0]

            self.assertEqual(data["bron"], AUDIT_BRC.component_name)
            self.assertEqual(data["hoofdObject"], f"http://testserver{besluit_url}")
            self.assertEqual(data["resourceUrl"], f"http://testserver{besluit_url}")
            self.assertEqual(
                data["wijzigingen"],
                {
                    "oud": None,
                    "nieuw": {
                        "url": f"http://testserver{besluit_url}",
                        "zaak": "",
                        "datum": "2026-05-05",
                        "besluittype": self.besluittype_url,
                        "toelichting": "desc",
                        "vervaldatum": None,
                        "vervalreden": "",
                        "ingangsdatum": "2026-05-05",
                        "verzenddatum": None,
                        "identificatie": "BESLUIT-2026-0000000001",
                        "bestuursorgaan": "",
                        "publicatiedatum": None,
                        "vervalredenWeergave": "",
                        "uiterlijkeReactiedatum": None,
                        "verantwoordelijkeOrganisatie": "517439943",
                    },
                },
            )

    def test_audittrail_in_zaken_api(self):
        besluiten_url = reverse("zaken:besluit-list")

        response = self.client.post(besluiten_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        audittrail = AuditTrail.objects.get()
        besluit = Besluit.objects.get()

        with self.subTest("audittrail model"):
            self.assertEqual(
                audittrail.bron, AUDIT_BRC.component_name
            )  # TODO see BRC_AUDIT comment
            self.assertEqual(audittrail.actie, "create")
            self.assertEqual(audittrail.resultaat, 201)
            self.assertEqual(
                audittrail.hoofd_object,
                f"http://testserver{reverse(besluit, namespace='besluiten')}",
            )
            self.assertEqual(audittrail.resource, "besluit")
            self.assertEqual(
                audittrail.resource_url,
                f"http://testserver{reverse(besluit, namespace='besluiten')}",
            )
            self.assertEqual(
                audittrail.resource_weergave, besluit.unique_representation()
            )

        with self.subTest("fetch from besluiten api"):
            url = reverse(
                "besluiten:audittrail-list", kwargs={"besluit_uuid": besluit.uuid}
            )

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()[0]

            self.assertEqual(data["bron"], AUDIT_BRC.component_name)
            self.assertEqual(
                data["hoofdObject"],
                f"http://testserver{reverse(besluit, namespace='besluiten')}",
            )
            self.assertEqual(
                data["resourceUrl"],
                f"http://testserver{reverse(besluit, namespace='besluiten')}",
            )
            self.assertEqual(
                data["wijzigingen"],
                {
                    "oud": None,
                    "nieuw": {
                        "url": f"http://testserver{reverse(besluit, namespace='besluiten')}",
                        "zaak": "",
                        "datum": "2026-05-05",
                        "besluittype": self.besluittype_url,
                        "toelichting": "desc",
                        "vervaldatum": None,
                        "vervalreden": "",
                        "ingangsdatum": "2026-05-05",
                        "verzenddatum": None,
                        "identificatie": "BESLUIT-2026-0000000001",
                        "bestuursorgaan": "",
                        "publicatiedatum": None,
                        "vervalredenWeergave": "",
                        "uiterlijkeReactiedatum": None,
                        "verantwoordelijkeOrganisatie": "517439943",
                    },
                },
            )

        with self.subTest("fetch from zaken api"):
            url = reverse(
                "zaken:audittrail-list", kwargs={"besluit_uuid": besluit.uuid}
            )

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()[0]

            self.assertEqual(data["bron"], AUDIT_BRC.component_name)
            self.assertEqual(
                data["hoofdObject"],
                f"http://testserver{reverse(besluit, namespace='besluiten')}",
            )
            self.assertEqual(
                data["resourceUrl"],
                f"http://testserver{reverse(besluit, namespace='besluiten')}",
            )
            self.assertEqual(
                data["wijzigingen"],
                {
                    "oud": None,
                    "nieuw": {
                        "url": f"http://testserver{reverse(besluit, namespace='besluiten')}",
                        "zaak": "",
                        "datum": "2026-05-05",
                        "besluittype": self.besluittype_url,
                        "toelichting": "desc",
                        "vervaldatum": None,
                        "vervalreden": "",
                        "ingangsdatum": "2026-05-05",
                        "verzenddatum": None,
                        "identificatie": "BESLUIT-2026-0000000001",
                        "bestuursorgaan": "",
                        "publicatiedatum": None,
                        "vervalredenWeergave": "",
                        "uiterlijkeReactiedatum": None,
                        "verantwoordelijkeOrganisatie": "517439943",
                    },
                },
            )

    def test_created_in_brc_updated_in_zrc(self):
        besluiten_url = reverse("besluiten:besluit-list")

        response = self.client.post(besluiten_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        besluit = Besluit.objects.get()

        besluit_url = reverse(besluit, namespace="zaken")
        response = self.client.patch(besluit_url, {"toelichting": "asc"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(AuditTrail.objects.count(), 2)
        self.assertEqual(len(besluit.audittrail), 2)

        create_trail = AuditTrail.objects.first()
        update_trail = AuditTrail.objects.last()

        self.assertEqual(create_trail.actie, "create")
        self.assertIn("/besluiten/api/v1/besluiten/", create_trail.hoofd_object)
        self.assertIn("/besluiten/api/v1/besluiten/", create_trail.resource_url)
        self.assertIn("/besluiten/api/v1/besluiten/", create_trail.nieuw["url"])

        self.assertEqual(update_trail.actie, "partial_update")
        self.assertIn("/besluiten/api/v1/besluiten/", update_trail.hoofd_object)
        self.assertIn("/besluiten/api/v1/besluiten/", update_trail.resource_url)
        self.assertIn("/besluiten/api/v1/besluiten/", update_trail.oud["url"])
        self.assertIn("/besluiten/api/v1/besluiten/", update_trail.nieuw["url"])
