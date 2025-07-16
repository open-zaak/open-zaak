# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact


from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.notes.constants import NotitieStatus, NotitieType
from vng_api_common.tests import reverse

from openzaak.tests.utils import JWTAuthMixin

from ..models import ZaakNotitie
from .factories import ZaakFactory, ZaakNotitieFactory


class ZaakNotitieTestCase(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @freeze_time("2025-01-01")
    def test_list(self):
        self.assertEqual(ZaakNotitie.objects.count(), 0)

        list_url = reverse("zaaknotitie-list")
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"], [])

        notitie = ZaakNotitieFactory.create()
        self.assertEqual(ZaakNotitie.objects.count(), 1)
        response = self.client.get(list_url)

        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(
            response.json()["results"],
            [
                {
                    "url": f"http://testserver{reverse(notitie)}",
                    "onderwerp": notitie.onderwerp,
                    "tekst": notitie.tekst,
                    "aangemaaktDoor": notitie.aangemaakt_door,
                    "notitieType": notitie.notitie_type.value,
                    "status": notitie.status.value,
                    "aanmaakdatum": notitie.aanmaakdatum.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "wijzigingsdatum": notitie.wijzigingsdatum.strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "gerelateerdAan": f"http://testserver{reverse(notitie.gerelateerd_aan)}",
                }
            ],
        )

    @freeze_time("2025-01-01")
    def test_detail(self):
        detail_url = reverse("zaaknotitie-detail", kwargs={"uuid": "123456"})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        notitie = ZaakNotitieFactory.create()
        detail_url = reverse("zaaknotitie-detail", kwargs={"uuid": notitie.uuid})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(response.json()["onderwerp"], notitie.onderwerp)
        self.assertEqual(
            data,
            {
                "url": f"http://testserver{reverse(notitie)}",
                "onderwerp": notitie.onderwerp,
                "tekst": notitie.tekst,
                "aangemaaktDoor": notitie.aangemaakt_door,
                "notitieType": notitie.notitie_type.value,
                "status": notitie.status.value,
                "aanmaakdatum": notitie.aanmaakdatum.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "wijzigingsdatum": notitie.wijzigingsdatum.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "gerelateerdAan": f"http://testserver{reverse(notitie.gerelateerd_aan)}",
            },
        )

    @freeze_time("2025-01-01")
    def test_create(self):
        self.assertEqual(ZaakNotitie.objects.count(), 0)
        list_url = reverse("zaaknotitie-list")
        zaak = ZaakFactory.create()
        data = {
            "onderwerp": "Test onderwerp",
            "tekst": "Test tekst",
            "aangemaaktDoor": "Test",
            "gerelateerdAan": f"http://testserver{reverse(zaak)}",
        }
        response = self.client.post(list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ZaakNotitie.objects.count(), 1)

        notitie = ZaakNotitie.objects.get()
        self.assertEqual(notitie.onderwerp, "Test onderwerp")
        self.assertEqual(notitie.tekst, "Test tekst")
        self.assertEqual(notitie.aangemaakt_door, "Test")
        self.assertEqual(notitie.gerelateerd_aan, zaak)

    def test_update(self):
        notitie = ZaakNotitieFactory.create(onderwerp="Old Value")
        detail_url = reverse("zaaknotitie-detail", kwargs={"uuid": notitie.uuid})
        data = {
            "onderwerp": "New Value",
            "tekst": notitie.tekst,
            "aangemaaktDoor": notitie.aangemaakt_door,
            "notitieType": notitie.notitie_type.value,
            "status": notitie.status.value,
            "gerelateerdAan": f"http://testserver{reverse(notitie.gerelateerd_aan)}",
        }

        response = self.client.put(detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        notitie = ZaakNotitie.objects.get()
        self.assertEqual(notitie.onderwerp, "New Value")

    def test_delete(self):
        notitie = ZaakNotitieFactory.create(onderwerp="Old Value")
        self.assertEqual(ZaakNotitie.objects.count(), 1)
        detail_url = reverse("zaaknotitie-detail", kwargs={"uuid": notitie.uuid})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ZaakNotitie.objects.count(), 0)

    @freeze_time("2025-01-01")
    def test_filters(self):
        ZaakNotitieFactory.create(
            onderwerp="test_onderwerp",
            tekst="test",
            status=NotitieStatus.CONCEPT.value,
            notitie_type=NotitieType.INTERN.value,
        )
        ZaakNotitieFactory.create(
            status=NotitieStatus.CONCEPT.value,
            notitie_type=NotitieType.EXTERN.value,
        )
        ZaakNotitieFactory.create(
            status=NotitieStatus.DEFINITIEF.value,
            notitie_type=NotitieType.INTERN.value,
        )
        list_url = reverse("zaaknotitie-list")

        with self.subTest("filter_status"):
            response = self.client.get(
                list_url, {"status": NotitieStatus.CONCEPT.value}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.json()["results"]), 2)
            self.assertEqual(
                response.json()["results"][0]["status"], NotitieStatus.CONCEPT.value
            )

        with self.subTest("filter_notitie_type"):
            response = self.client.get(
                list_url, {"notitieType": NotitieType.EXTERN.value}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.json()["results"]), 1)
            self.assertEqual(
                response.json()["results"][0]["notitieType"], NotitieType.EXTERN.value
            )

        with self.subTest("filter_onderwerp"):
            response = self.client.get(list_url, {"onderwerp": "wrong"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.json()["results"]), 0)

            response = self.client.get(list_url, {"onderwerp": "test_onderwerp"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.json()["results"]), 1)

            response = self.client.get(list_url, {"onderwerp__icontains": "test_"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.json()["results"]), 1)

        with self.subTest("filter_aanmaakdatum"):
            response = self.client.get(list_url, {"aanmaakdatum__date": "2025-01-01"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.json()["results"]), 3)
            response = self.client.get(list_url, {"aanmaakdatum__gt": "2025-01-01"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.json()["results"]), 0)

            response = self.client.get(list_url, {"aanmaakdatum__lt": "2025-01-01"})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.json()["results"]), 0)

            response = self.client.get(
                list_url, {"aanmaakdatum__date__lte": "2025-01-01"}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.json()["results"]), 3)
