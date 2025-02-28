# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from datetime import datetime

from django.test import override_settings
from django.utils import timezone

from freezegun import freeze_time
from rest_framework import status
from vng_api_common.constants import RelatieAarden
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy
from vng_api_common.validators import IsImmutableValidator
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import (
    ZaakTypeInformatieObjectTypeFactory,
)
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.tests.utils import APICMISTestCase, JWTAuthMixin, require_cmis

from ...documenten.models import EnkelvoudigInformatieObject, ObjectInformatieObject
from ..models import Zaak, ZaakInformatieObject
from .factories import StatusFactory, ZaakFactory, ZaakInformatieObjectFactory


@require_cmis
@override_settings(CMIS_ENABLED=True)
class ZaakInformatieObjectCMISAPITests(JWTAuthMixin, APICMISTestCase):

    list_url = reverse_lazy(ZaakInformatieObject)
    heeft_alle_autorisaties = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_root="http://example.com/documenten/api/v1/", api_type=APITypes.drc
        )

    @freeze_time("2018-09-19T12:25:19+0200")
    def test_create(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"

        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )
        status_ = StatusFactory.create(zaak=zaak)
        status_url = reverse(status_)

        titel = "some titel"
        beschrijving = "some beschrijving"
        content = {
            "informatieobject": io_url,
            "zaak": f"http://testserver{zaak_url}",
            "titel": titel,
            "beschrijving": beschrijving,
            "aardRelatieWeergave": "bla",  # Should be ignored by the API
            "vernietigingsdatum": "2023-01-02T00:00:00Z",
            "status": f"http://testserver{status_url}",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Test database
        self.assertEqual(ZaakInformatieObject.objects.count(), 1)
        stored_object = ZaakInformatieObject.objects.get()
        self.assertEqual(stored_object.zaak, zaak)
        self.assertEqual(stored_object.aard_relatie, RelatieAarden.hoort_bij)

        expected_url = reverse(stored_object)

        expected_response = content.copy()
        expected_response.update(
            {
                "url": f"http://testserver{expected_url}",
                "uuid": str(stored_object.uuid),
                "titel": titel,
                "beschrijving": beschrijving,
                "registratiedatum": "2018-09-19T10:25:19Z",
                "aardRelatieWeergave": RelatieAarden.hoort_bij.label,
            }
        )

        self.assertEqual(response.json(), expected_response)

        self.assertEqual(ObjectInformatieObject.objects.count(), 1)
        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 1)

    def test_zaaktype_with_invalid_characters_in_omschrijving(self):
        """
        The CMIS-adapter uses the zaaktype omschrijving to give the name to the zaaktype
        folder. Invalid filename characters in the omschrijving field need to be handled.
        """
        zaak = ZaakFactory.create()

        zaak.zaaktype.zaaktype_omschrijving = "Invalid/filename/characters/present"
        zaak.zaaktype.save()

        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"

        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )

        titel = "some titel"
        beschrijving = "some beschrijving"
        content = {
            "informatieobject": io_url,
            "zaak": f"http://testserver{zaak_url}",
            "titel": titel,
            "beschrijving": beschrijving,
            "aardRelatieWeergave": "bla",  # Should be ignored by the API
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    @freeze_time("2018-09-20 12:00:00")
    def test_registratiedatum_ignored(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"

        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )
        content = {
            "informatieobject": io_url,
            "zaak": f"http://testserver{zaak_url}",
            "registratiedatum": "2018-09-19T12:25:20+0200",
        }

        # Send to the API
        self.client.post(self.list_url, content)

        oio = ZaakInformatieObject.objects.get()

        self.assertEqual(
            oio.registratiedatum,
            datetime(2018, 9, 20, 12, 0, 0).replace(tzinfo=timezone.utc),
        )

    def test_duplicate_object(self):
        """
        Test the (informatieobject, object) unique together validation.
        """
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"

        zio_type = ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype__concept=False, zaaktype__concept=False
        )
        zio = ZaakInformatieObjectFactory.create(
            informatieobject=eio_url,
            informatieobject__latest_version__informatieobjecttype=zio_type.informatieobjecttype,
        )
        zaak_url = reverse(zio.zaak)

        content = {
            "informatieobject": eio_url,
            "zaak": f"http://testserver{zaak_url}",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unique")

    @freeze_time("2018-09-20 12:00:00")
    def test_read_zaakinformatieobject(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://testserver{reverse(eio)}"
        zio = ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        zio_detail_url = reverse(zio)

        response = self.client.get(zio_detail_url)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        zaak_url = reverse(zio.zaak)
        expected = {
            "url": f"http://testserver{zio_detail_url}",
            "uuid": str(zio.uuid),
            "informatieobject": eio_url,
            "zaak": f"http://testserver{zaak_url}",
            "aardRelatieWeergave": RelatieAarden.hoort_bij.label,
            "titel": "",
            "beschrijving": "",
            "registratiedatum": "2018-09-20T12:00:00Z",
            "status": None,
            "vernietigingsdatum": None,
        }

        self.assertEqual(response.json(), expected)

    @override_settings(ALLOWED_HOSTS=["testserver", "example.com"])
    def test_filter_by_zaak(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        zio = ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        zaak_url = reverse(zio.zaak)
        zio_list_url = reverse("zaakinformatieobject-list")

        response = self.client.get(
            zio_list_url,
            {"zaak": f"http://example.com{zaak_url}"},
            headers={"host": "example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["zaak"], f"http://example.com{zaak_url}")

    @override_settings(ALLOWED_HOSTS=["testserver", "example.com"])
    def test_filter_by_informatieobject(self):
        # Create two ZIOs
        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = f"http://example.com{reverse(eio1)}"

        ZaakInformatieObjectFactory.create(informatieobject=eio1_url)

        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = f"http://example.com{reverse(eio2)}"

        ZaakInformatieObjectFactory.create(informatieobject=eio2_url)

        zio_list_url = reverse("zaakinformatieobject-list")

        # Test that only 1 of the 2 ZIOs is returned
        response = self.client.get(
            zio_list_url,
            {"informatieobject": eio1_url},
            headers={"host": "example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["informatieobject"], eio1_url)

    def test_update_zaak_and_informatieobject_fails(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = f"http://testserver{reverse(eio1)}"
        zio = ZaakInformatieObjectFactory.create(informatieobject=eio1_url)
        zio_detail_url = reverse(zio)
        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = f"http://testserver{reverse(eio2)}"

        response = self.client.put(
            zio_detail_url,
            {
                "zaak": f"http://testserver{zaak_url}",
                "informatieobject": eio2_url,
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        for field in ["zaak", "informatieobject"]:
            with self.subTest(field=field):
                error = get_validation_errors(response, field)
                self.assertEqual(error["code"], IsImmutableValidator.code)

    def test_partial_update_zaak_and_informatieobject_fails(self):
        eio1 = EnkelvoudigInformatieObjectFactory.create()
        eio1_url = eio1.get_url()
        zio = ZaakInformatieObjectFactory.create(informatieobject=eio1_url)
        zio_detail_url = reverse(zio)

        eio2 = EnkelvoudigInformatieObjectFactory.create()
        eio2_url = f"http://testserver{reverse(eio2)}"
        other_zaak = ZaakFactory.create()

        response = self.client.patch(
            zio_detail_url,
            {
                "zaak": f"http://testserver{reverse(other_zaak)}",
                "informatieobject": eio2_url,
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        for field in ["zaak", "informatieobject"]:
            with self.subTest(field=field):
                error = get_validation_errors(response, field)
                self.assertEqual(error["code"], IsImmutableValidator.code)

    def test_update_zio_metadata(self):
        zaak = ZaakFactory.create()
        zaak_url = reverse(zaak)
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = f"http://testserver{reverse(io)}"

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaak.zaaktype, informatieobjecttype=io.informatieobjecttype
        )

        zio = ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io_url)
        zio_detail_url = reverse(zio)

        response = self.client.put(
            zio_detail_url,
            {
                "zaak": f"http://testserver{zaak_url}",
                "informatieobject": io_url,
                "titel": "updated title",
                "beschrijving": "same",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(response.data["titel"], "updated title")
        self.assertEqual(response.data["beschrijving"], "same")

        zio.refresh_from_db()
        self.assertEqual(zio.titel, "updated title")
        self.assertEqual(zio.beschrijving, "same")

    def test_partial_update_zio_metadata(self):
        zaak = ZaakFactory.create()
        io = EnkelvoudigInformatieObjectFactory.create()
        io_url = io.get_url()

        ZaakTypeInformatieObjectTypeFactory.create(
            zaaktype=zaak.zaaktype, informatieobjecttype=io.informatieobjecttype
        )

        zio = ZaakInformatieObjectFactory.create(zaak=zaak, informatieobject=io_url)
        zio_detail_url = reverse(zio)

        response = self.client.patch(
            zio_detail_url, {"titel": "updated title", "beschrijving": "same"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(response.data["titel"], "updated title")
        self.assertEqual(response.data["beschrijving"], "same")

        zio.refresh_from_db()
        self.assertEqual(zio.titel, "updated title")
        self.assertEqual(zio.beschrijving, "same")

    @freeze_time("2018-09-19T12:25:19+0200")
    def test_delete(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = eio.get_url()
        zio = ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        zio_url = reverse(zio)

        response = self.client.delete(zio_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        # Relation is gone, zaak still exists.
        self.assertFalse(ZaakInformatieObject.objects.exists())
        self.assertTrue(Zaak.objects.exists())

    def test_representation(self):
        zaak = ZaakFactory.create()
        io = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype__concept=False
        )
        io_url = f"http://testserver{reverse(io)}"

        ZaakTypeInformatieObjectTypeFactory.create(
            informatieobjecttype=io.informatieobjecttype, zaaktype=zaak.zaaktype
        )
        zio = ZaakInformatieObjectFactory.create(
            zaak=zaak,
            informatieobject=io_url,
        )
        zio_representation = str(zio)
        expected_representation = f"{zaak.identificatie} - {io_url}"
        self.assertEqual(expected_representation, zio_representation)

    def test_delete_document_unrelated_to_zaak(self):
        # Create a document related to a zaak
        eio_related = EnkelvoudigInformatieObjectFactory.create()
        eio_related_url = f"http://example.com{reverse(eio_related)}"
        ZaakInformatieObjectFactory.create(informatieobject=eio_related_url)

        # Create a document unrelated to a zaak
        eio_unrelated = EnkelvoudigInformatieObjectFactory.create()
        eio_unrelated_url = f"http://example.com{reverse(eio_unrelated)}"

        response = self.client.delete(eio_unrelated_url)

        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
