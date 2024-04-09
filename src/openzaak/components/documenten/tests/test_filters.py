# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.contrib.sites.models import Site
from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.besluiten.tests.factories import (
    BesluitFactory,
    BesluitInformatieObjectFactory,
)
from openzaak.components.zaken.tests.factories import (
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from openzaak.tests.utils import JWTAuthMixin

from ..models import (
    EnkelvoudigInformatieObject,
    Gebruiksrechten,
    ObjectInformatieObject,
)
from .factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
    GebruiksrechtenFactory,
)


class EnkelvoudigInformatieObjectFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_locked_filter(self):
        locked_canonical = EnkelvoudigInformatieObjectCanonicalFactory(lock="locked")
        EnkelvoudigInformatieObjectFactory(canonical=locked_canonical)
        EnkelvoudigInformatieObjectFactory()

        with self.subTest("locked_objects"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject), {"locked": True}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["locked"], True)

        with self.subTest("unlocked_objects"):
            response = self.client.get(
                reverse(EnkelvoudigInformatieObject), {"locked": False}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["locked"], False)

    @override_settings(
        NOTIFICATIONS_DISABLED=True,
        ALLOWED_HOSTS=["testserver", "testserver.com"],
    )
    def test_zaak_filter(self):
        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        zaak = ZaakFactory.create()
        eio = EnkelvoudigInformatieObjectFactory.create()
        EnkelvoudigInformatieObjectFactory.create()
        EnkelvoudigInformatieObjectFactory.create()

        ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=eio.canonical)
        zaak_url = reverse(zaak)
        ZaakInformatieObjectFactory.create_batch(3)
        response = self.client.get(
            reverse(EnkelvoudigInformatieObject),
            {"zaak": f"http://testserver.com{zaak_url}"},
            HTTP_HOST="testserver.com",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)

        with self.subTest("can_only_filter_on_zaak"):
            besluit = BesluitFactory.create()
            BesluitInformatieObjectFactory.create(
                besluit=besluit, informatieobject=eio.canonical
            )
            besluit_url = reverse(besluit)

            response = self.client.get(
                reverse(EnkelvoudigInformatieObject),
                {"zaak": f"http://testserver.com{besluit_url}"},
                HTTP_HOST="testserver.com",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 0)


class GebruiksrechtenFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        response = self.client.get(
            reverse(Gebruiksrechten), {"informatieobject": "bla"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobject")
        self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version__informatieobjecttype__concept=False
        )
        GebruiksrechtenFactory.create(informatieobject=eio)

        response = self.client.get(
            reverse(Gebruiksrechten), {"informatieobject": "https://google.com"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


class ObjectInformatieObjectFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_by_invalid_url(self):
        for query_param in ["informatieobject", "object"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ObjectInformatieObject), {query_param: "bla"}
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                error = get_validation_errors(response, query_param)
                self.assertEqual(error["code"], "invalid")

    def test_filter_by_valid_url_object_does_not_exist(self):
        for query_param in ["informatieobject", "object"]:
            with self.subTest(query_param=query_param):
                response = self.client.get(
                    reverse(ObjectInformatieObject), {query_param: "https://google.com"}
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data, [])
