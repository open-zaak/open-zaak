# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact


from rest_framework import status
from rest_framework.test import APITestCase

from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)
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
