# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid
from base64 import b64encode
from datetime import date

from django.test import override_settings, tag
from django.utils import timezone

import requests_mock
from freezegun import freeze_time
from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors, reverse, reverse_lazy
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.zaken.tests.factories import ZaakInformatieObjectFactory
from openzaak.tests.utils import JWTAuthMixin, MockSchemasMixin

from ..models import EnkelvoudigInformatieObject, EnkelvoudigInformatieObjectCanonical
from .factories import EnkelvoudigInformatieObjectFactory
from .utils import (
    get_catalogus_response,
    get_informatieobjecttype_response,
    get_operation_url,
)


@freeze_time("2018-06-27 12:12:12")
@temp_private_root()
class EnkelvoudigInformatieObjectAPITests(JWTAuthMixin, APITestCase):

    list_url = reverse_lazy(EnkelvoudigInformatieObject)
    heeft_alle_autorisaties = True

    def test_list(self):
        EnkelvoudigInformatieObjectFactory.create_batch(4)
        url = reverse("enkelvoudiginformatieobject-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data["results"]), 4)

    def test_create(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
            "verschijningsvorm": "Vorm A",
            "trefwoorden": ["some", "other"],
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Test database
        stored_object = EnkelvoudigInformatieObject.objects.get()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 1)
        self.assertEqual(stored_object.identificatie, content["identificatie"])
        self.assertEqual(stored_object.bronorganisatie, "159351741")
        self.assertEqual(stored_object.creatiedatum, date(2018, 6, 27))
        self.assertEqual(stored_object.titel, "detailed summary")
        self.assertEqual(stored_object.auteur, "test_auteur")
        self.assertEqual(stored_object.formaat, "txt")
        self.assertEqual(stored_object.taal, "eng")
        self.assertEqual(stored_object.versie, 1)
        self.assertAlmostEqual(stored_object.begin_registratie, timezone.now())
        self.assertEqual(stored_object.bestandsnaam, "dummy.txt")
        self.assertEqual(stored_object.inhoud.read(), b"some file content")
        self.assertEqual(stored_object.link, "http://een.link")
        self.assertEqual(stored_object.beschrijving, "test_beschrijving")
        self.assertEqual(stored_object.informatieobjecttype, informatieobjecttype)
        self.assertEqual(stored_object.vertrouwelijkheidaanduiding, "openbaar")
        self.assertEqual(stored_object.verschijningsvorm, "Vorm A")
        self.assertEqual(stored_object.trefwoorden, ["some", "other"])

        expected_url = reverse(stored_object)
        expected_file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=stored_object.uuid
        )

        expected_response = content.copy()
        expected_response.update(
            {
                "url": f"http://testserver{expected_url}",
                "inhoud": f"http://testserver{expected_file_url}?versie=1",
                "versie": 1,
                "bestandsdelen": [],
                "beginRegistratie": stored_object.begin_registratie.isoformat().replace(
                    "+00:00", "Z"
                ),
                "vertrouwelijkheidaanduiding": "openbaar",
                "bestandsomvang": stored_object.inhoud.size,
                "integriteit": {"algoritme": "", "waarde": "", "datum": None},
                "ontvangstdatum": None,
                "verzenddatum": None,
                "ondertekening": {"soort": "", "datum": None},
                "indicatieGebruiksrecht": None,
                "status": "",
                "locked": False,
                "lock": "",
                "verschijningsvorm": "Vorm A",
            }
        )

        response_data = response.json()
        self.assertEqual(sorted(response_data.keys()), sorted(expected_response.keys()))

        for key in response_data.keys():
            with self.subTest(field=key):
                self.assertEqual(response_data[key], expected_response[key])

    def test_create_with_very_big_bestandsomvang(self):
        three_giga_bites = 3_221_225_472  # 3gb in bytes
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)

        content = {
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "bestandsomvang": three_giga_bites,
            "inhoud": None,
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.json()
        self.assertEqual(data["bestandsomvang"], three_giga_bites)

    @tag("gh-1306")
    def test_create_identificatie_all_characters_allowed(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        content = {
            "identificatie": "some docüment",
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
            "verschijningsvorm": "Vorm A",
            "trefwoorden": ["some", "other"],
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Test database
        stored_object = EnkelvoudigInformatieObject.objects.get()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 1)
        self.assertEqual(stored_object.identificatie, content["identificatie"])
        self.assertEqual(stored_object.bronorganisatie, "159351741")
        self.assertEqual(stored_object.creatiedatum, date(2018, 6, 27))
        self.assertEqual(stored_object.titel, "detailed summary")
        self.assertEqual(stored_object.auteur, "test_auteur")
        self.assertEqual(stored_object.formaat, "txt")
        self.assertEqual(stored_object.taal, "eng")
        self.assertEqual(stored_object.versie, 1)
        self.assertAlmostEqual(stored_object.begin_registratie, timezone.now())
        self.assertEqual(stored_object.bestandsnaam, "dummy.txt")
        self.assertEqual(stored_object.inhoud.read(), b"some file content")
        self.assertEqual(stored_object.link, "http://een.link")
        self.assertEqual(stored_object.beschrijving, "test_beschrijving")
        self.assertEqual(stored_object.informatieobjecttype, informatieobjecttype)
        self.assertEqual(stored_object.vertrouwelijkheidaanduiding, "openbaar")
        self.assertEqual(stored_object.verschijningsvorm, "Vorm A")
        self.assertEqual(stored_object.trefwoorden, ["some", "other"])

        expected_url = reverse(stored_object)
        expected_file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=stored_object.uuid
        )

        expected_response = content.copy()
        expected_response.update(
            {
                "url": f"http://testserver{expected_url}",
                "inhoud": f"http://testserver{expected_file_url}?versie=1",
                "versie": 1,
                "bestandsdelen": [],
                "beginRegistratie": stored_object.begin_registratie.isoformat().replace(
                    "+00:00", "Z"
                ),
                "vertrouwelijkheidaanduiding": "openbaar",
                "bestandsomvang": stored_object.inhoud.size,
                "integriteit": {"algoritme": "", "waarde": "", "datum": None},
                "ontvangstdatum": None,
                "verzenddatum": None,
                "ondertekening": {"soort": "", "datum": None},
                "indicatieGebruiksrecht": None,
                "status": "",
                "locked": False,
                "lock": "",
                "verschijningsvorm": "Vorm A",
            }
        )

        response_data = response.json()
        self.assertEqual(sorted(response_data.keys()), sorted(expected_response.keys()))

        for key in response_data.keys():
            with self.subTest(field=key):
                self.assertEqual(response_data[key], expected_response[key])

    def test_create_without_identificatie(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        content = {
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Test database
        stored_object = EnkelvoudigInformatieObject.objects.get()

        self.assertEqual(EnkelvoudigInformatieObject.objects.count(), 1)

        # Test generation of human readable identificatie
        self.assertEqual(stored_object.identificatie, "DOCUMENT-2018-0000000001")

    def test_create_two_docs_with_same_identificatie_and_bronorganisatie(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        content = {
            "identificatie": "12345",
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response = self.client.post(self.list_url, content)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertEqual(len(response.data["invalid_params"]), 1)
        self.assertEqual(
            response.data["invalid_params"][0]["code"], "identificatie-niet-uniek"
        )

    def test_create_fail_informatieobjecttype_max_length(self):
        informatieobjecttype = InformatieObjectTypeFactory.create()
        informatieobjecttype_url = reverse(informatieobjecttype)
        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver/some-very-long-url-addres-which-exceeds-maximum-"
            f"length-of-hyperlinkedrelatedfield/aaaaaaaaaaaaaaaaaaaaaaaaa/"
            f"{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "informatieobjecttype")
        self.assertEqual(error["code"], "max_length")

    def test_read(self):
        test_object = EnkelvoudigInformatieObjectFactory.create()
        # Retrieve from the API
        detail_url = reverse(test_object)

        response = self.client.get(detail_url)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=test_object.uuid
        )
        expected = {
            "url": f"http://testserver{detail_url}",
            "identificatie": str(test_object.identificatie),
            "bronorganisatie": test_object.bronorganisatie,
            "bestandsdelen": [],
            "creatiedatum": "2018-06-27",
            "titel": "some titel",
            "auteur": "some auteur",
            "status": "",
            "formaat": "some formaat",
            "taal": "nld",
            "beginRegistratie": test_object.begin_registratie.isoformat().replace(
                "+00:00", "Z"
            ),
            "versie": 1,
            "bestandsnaam": "",
            "inhoud": f"http://testserver{file_url}?versie=1",
            "bestandsomvang": test_object.inhoud.size,
            "link": "",
            "beschrijving": "",
            "ontvangstdatum": None,
            "verzenddatum": None,
            "ondertekening": {"soort": "", "datum": None},
            "indicatieGebruiksrecht": None,
            "vertrouwelijkheidaanduiding": "openbaar",
            "integriteit": {"algoritme": "", "waarde": "", "datum": None},
            "informatieobjecttype": f"http://testserver{reverse(test_object.informatieobjecttype)}",
            "locked": False,
            "verschijningsvorm": "",
            "trefwoorden": [],
        }

        response_data = response.json()
        self.assertEqual(sorted(response_data.keys()), sorted(expected.keys()))

        for key in response_data.keys():
            with self.subTest(field=key):
                self.assertEqual(response_data[key], expected[key])

    def test_bestandsomvang(self):
        """
        Assert that the API shows the filesize.
        """
        test_object = EnkelvoudigInformatieObjectFactory.create(
            inhoud__data=b"some content"
        )

        # Retrieve from the API
        detail_url = reverse(
            "enkelvoudiginformatieobject-detail",
            kwargs={"version": "1", "uuid": test_object.uuid},
        )

        response = self.client.get(detail_url)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["bestandsomvang"], 12)  # 12 bytes

    def test_integrity_empty(self):
        """
        Assert that integrity is optional.
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-12-13",
            "titel": "Voorbeelddocument",
            "auteur": "test_auteur",
            "formaat": "text/plain",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "vertrouwelijkheidaanduiding": "openbaar",
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "integriteit": None,
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stored_object = EnkelvoudigInformatieObject.objects.get()
        self.assertEqual(
            stored_object.integriteit, {"algoritme": "", "waarde": "", "datum": None}
        )

    def test_integrity_provided(self):
        """
        Assert that integrity is saved.
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-12-13",
            "titel": "Voorbeelddocument",
            "auteur": "test_auteur",
            "formaat": "text/plain",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "vertrouwelijkheidaanduiding": "openbaar",
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "integriteit": {
                "algoritme": "md5",
                "waarde": "27c3a009a3cbba674d0b3e836f2d4685",
                "datum": "2018-12-13",
            },
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stored_object = EnkelvoudigInformatieObject.objects.get()
        self.assertEqual(
            stored_object.integriteit,
            {
                "algoritme": "md5",
                "waarde": "27c3a009a3cbba674d0b3e836f2d4685",
                "datum": date(2018, 12, 13),
            },
        )

    def test_filter_by_identification(self):
        EnkelvoudigInformatieObjectFactory.create(identificatie="foo")
        EnkelvoudigInformatieObjectFactory.create(identificatie="bar")

        response = self.client.get(self.list_url, {"identificatie": "foo"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]

        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["identificatie"], "foo")

    def test_destroy_no_relations_allowed(self):
        """
        Assert that destroying is possible when there are no relations.
        """
        eio = EnkelvoudigInformatieObjectFactory.create()
        url = reverse(eio)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(EnkelvoudigInformatieObject.objects.exists())

    def test_destroy_with_relations_not_allowed(self):
        """
        Assert that destroying is not possible when there are relations.
        """
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_path = reverse(eio)
        ZaakInformatieObjectFactory.create(informatieobject=eio.canonical)

        response = self.client.delete(eio_path)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "pending-relations")

    def test_destroy_locked_not_allowed(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        url = reverse(eio)
        self.client.post(f"{url}/lock")

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "destroy-locked")
        self.assertTrue(EnkelvoudigInformatieObject.objects.filter(id=eio.id).exists())

    def test_validate_unknown_query_params(self):
        EnkelvoudigInformatieObjectFactory.create_batch(2)
        url = reverse(EnkelvoudigInformatieObject)

        response = self.client.get(url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")

    def test_eio_download_with_accept_application_octet_stream_header(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            beschrijving="beschrijving1", inhoud__data=b"inhoud1"
        )

        eio_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio.uuid
        )

        response = self.client.get(
            eio_url, headers={"accept": "application/octet-stream"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        try:
            self.assertEqual(list(response.streaming_content)[0], b"inhoud1")
        except AttributeError:
            self.assertEqual(response._container[0], b"inhoud1")

    def test_invalid_inhoud(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": [1, 2, 3],
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        # Test response
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "inhoud")

        self.assertEqual(error["code"], "invalid")

    def test_inhoud_invalid_utf8_char_not_b64_encoded(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": "dummy.txt",
            "inhoud": "<",
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": "openbaar",
        }

        # Send to the API
        response = self.client.post(self.list_url, content)

        # Test response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_download_deleted_eio(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            beschrijving="beschrijving1", inhoud__data=b"inhoud1"
        )

        eio_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio.uuid
        )

        response = self.client.delete(reverse(eio))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(
            eio_url, headers={"accept": "application/octet-stream"}
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(SENDFILE_BACKEND="django_sendfile.backends.simple")
class EnkelvoudigInformatieObjectVersionHistoryAPITests(JWTAuthMixin, APITestCase):
    list_url = reverse_lazy(EnkelvoudigInformatieObject)
    heeft_alle_autorisaties = True

    def test_eio_update(self):
        iotype1, iotype2 = InformatieObjectTypeFactory.create_batch(2, concept=False)
        eio = EnkelvoudigInformatieObjectFactory.create(
            beschrijving="beschrijving1", informatieobjecttype=iotype1
        )

        iotype2_url = reverse(
            "informatieobjecttype-detail", kwargs={"uuid": iotype2.uuid}
        )
        eio_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}
        )

        eio_response = self.client.get(eio_url)
        eio_data = eio_response.data

        lock = self.client.post(f"{eio_url}/lock").data["lock"]
        eio_data.update(
            {
                "beschrijving": "beschrijving2",
                "inhoud": b64encode(b"aaaaa"),
                "bestandsomvang": 5,
                "lock": lock,
                "informatieobjecttype": f"http://testserver{iotype2_url}",
            }
        )

        for i in ["integriteit", "ondertekening"]:
            eio_data.pop(i)

        response = self.client.put(eio_url, eio_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertEqual(response_data["beschrijving"], "beschrijving2")

        eios = EnkelvoudigInformatieObject.objects.filter(uuid=eio.uuid).order_by(
            "-versie"
        )

        self.assertEqual(len(eios), 2)

        latest_version = eios.first()
        self.assertEqual(latest_version.versie, 2)
        self.assertEqual(latest_version.beschrijving, "beschrijving2")
        self.assertEqual(latest_version.informatieobjecttype, iotype2)

        first_version = eios[1]
        self.assertEqual(first_version.versie, 1)
        self.assertEqual(first_version.beschrijving, "beschrijving1")
        self.assertEqual(first_version.informatieobjecttype, iotype1)

    def test_eio_update_with_empty_content(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            beschrijving="beschrijving1", informatieobjecttype__concept=False
        )

        eio_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}
        )

        eio_response = self.client.get(eio_url)
        eio_data = eio_response.data

        lock = self.client.post(f"{eio_url}/lock").data["lock"]
        eio_data["lock"] = lock
        for i in ["integriteit", "ondertekening", "inhoud", "bestandsomvang"]:
            eio_data.pop(i)

        response = self.client.put(eio_url, eio_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertIsNone(response_data["inhoud"])
        self.assertIsNone(response_data["bestandsomvang"])

        eios = EnkelvoudigInformatieObject.objects.filter(uuid=eio.uuid).order_by(
            "-versie"
        )

        self.assertEqual(len(eios), 2)

        latest_version = eios.first()
        self.assertEqual(latest_version.versie, 2)
        self.assertEqual(str(latest_version.inhoud), "")
        self.assertIsNone(latest_version.bestandsomvang)

        first_version = eios[1]
        self.assertEqual(first_version.versie, 1)
        self.assertNotEqual(str(first_version.inhoud), "")
        self.assertIsNotNone(first_version.bestandsomvang)

    def test_eio_partial_update(self):
        eio = EnkelvoudigInformatieObjectFactory.create(beschrijving="beschrijving1")

        eio_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}
        )
        lock = self.client.post(f"{eio_url}/lock").data["lock"]
        response = self.client.patch(
            eio_url, {"beschrijving": "beschrijving2", "lock": lock}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertEqual(response_data["beschrijving"], "beschrijving2")

        eios = EnkelvoudigInformatieObject.objects.filter(uuid=eio.uuid).order_by(
            "-versie"
        )
        self.assertEqual(len(eios), 2)

        latest_version = eios.first()
        self.assertEqual(latest_version.versie, 2)
        self.assertEqual(latest_version.beschrijving, "beschrijving2")

        first_version = eios[1]
        self.assertEqual(first_version.versie, 1)
        self.assertEqual(first_version.beschrijving, "beschrijving1")

    def test_eio_delete(self):
        eio = EnkelvoudigInformatieObjectFactory.create(beschrijving="beschrijving1")

        eio_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}
        )
        lock = self.client.post(f"{eio_url}/lock").data["lock"]
        self.client.patch(eio_url, {"beschrijving": "beschrijving2", "lock": lock})
        self.client.post(f"{eio_url}/unlock", {"lock": lock})

        response = self.client.delete(eio_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(EnkelvoudigInformatieObjectCanonical.objects.exists())
        self.assertFalse(EnkelvoudigInformatieObject.objects.exists())

    def test_eio_detail_retrieves_latest_version(self):
        eio = EnkelvoudigInformatieObjectFactory.create(beschrijving="beschrijving1")

        eio_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}
        )
        lock = self.client.post(f"{eio_url}/lock").data["lock"]
        self.client.patch(eio_url, {"beschrijving": "beschrijving2", "lock": lock})

        response = self.client.get(eio_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["beschrijving"], "beschrijving2")

    def test_eio_list_shows_latest_versions(self):
        eio1 = EnkelvoudigInformatieObjectFactory.create(beschrijving="object1")

        eio1_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio1.uuid}
        )
        lock1 = self.client.post(f"{eio1_url}/lock").data["lock"]
        self.client.patch(eio1_url, {"beschrijving": "object1 versie2", "lock": lock1})

        eio2 = EnkelvoudigInformatieObjectFactory.create(beschrijving="object2")

        eio2_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio2.uuid}
        )
        lock2 = self.client.post(f"{eio2_url}/lock").data["lock"]
        self.client.patch(eio2_url, {"beschrijving": "object2 versie2", "lock": lock2})

        response = self.client.get(reverse(EnkelvoudigInformatieObject))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.data["results"]
        self.assertEqual(len(response_data), 2)

        self.assertEqual(response_data[0]["beschrijving"], "object1 versie2")
        self.assertEqual(response_data[1]["beschrijving"], "object2 versie2")

    def test_eio_detail_filter_by_version(self):
        eio = EnkelvoudigInformatieObjectFactory.create(beschrijving="beschrijving1")

        eio_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}
        )
        lock = self.client.post(f"{eio_url}/lock").data["lock"]
        self.client.patch(eio_url, {"beschrijving": "beschrijving2", "lock": lock})

        response = self.client.get(eio_url, {"versie": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["beschrijving"], "beschrijving1")

    def test_eio_detail_filter_by_wrong_version_gives_404(self):
        eio = EnkelvoudigInformatieObjectFactory.create(beschrijving="beschrijving1")

        eio_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}
        )
        lock = self.client.post(f"{eio_url}/lock").data["lock"]
        self.client.patch(eio_url, {"beschrijving": "beschrijving2", "lock": lock})

        response = self.client.get(eio_url, {"versie": 100})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_eio_detail_filter_by_registratie_op(self):
        with freeze_time("2019-01-01 12:00:00"):
            eio = EnkelvoudigInformatieObjectFactory.create(
                beschrijving="beschrijving1"
            )

        eio_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}
        )
        lock = self.client.post(f"{eio_url}/lock").data["lock"]
        with freeze_time("2019-01-01 13:00:00"):
            self.client.patch(eio_url, {"beschrijving": "beschrijving2", "lock": lock})

        response = self.client.get(eio_url, {"registratieOp": "2019-01-01T12:00:00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["beschrijving"], "beschrijving1")

    @freeze_time("2019-01-01 12:00:00")
    def test_eio_detail_filter_by_wrong_registratie_op_gives_404(self):
        eio = EnkelvoudigInformatieObjectFactory.create(beschrijving="beschrijving1")

        eio_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}
        )
        lock = self.client.post(f"{eio_url}/lock").data["lock"]
        self.client.patch(eio_url, {"beschrijving": "beschrijving2", "lock": lock})

        response = self.client.get(eio_url, {"registratieOp": "2019-01-01T11:59:00"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_eio_download_content_filter_by_version(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            beschrijving="beschrijving1", inhoud__data=b"inhoud1"
        )

        eio_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}
        )
        lock = self.client.post(f"{eio_url}/lock").data["lock"]
        self.client.patch(
            eio_url,
            {
                "inhoud": b64encode(b"inhoud2"),
                "beschrijving": "beschrijving2",
                "lock": lock,
            },
        )

        response = self.client.get(eio_url, {"versie": "1"})
        response_download = self.client.get(response.data["inhoud"])

        try:
            self.assertEqual(list(response_download.streaming_content)[0], b"inhoud1")
        except AttributeError:
            self.assertEqual(response_download.content, b"inhoud1")

    def test_eio_download_content_filter_by_registratie(self):
        with freeze_time("2019-01-01 12:00:00"):
            eio = EnkelvoudigInformatieObjectFactory.create(
                beschrijving="beschrijving1", inhoud__data=b"inhoud1"
            )

        eio_url = reverse(
            "enkelvoudiginformatieobject-detail", kwargs={"uuid": eio.uuid}
        )
        lock = self.client.post(f"{eio_url}/lock").data["lock"]
        with freeze_time("2019-01-01 13:00:00"):
            self.client.patch(
                eio_url,
                {
                    "inhoud": b64encode(b"inhoud2"),
                    "beschrijving": "beschrijving2",
                    "lock": lock,
                },
            )

        response = self.client.get(eio_url, {"registratieOp": "2019-01-01T12:00:00"})
        response_download = self.client.get(response.data["inhoud"])

        try:
            self.assertEqual(list(response_download.streaming_content)[0], b"inhoud1")
        except AttributeError:
            self.assertEqual(response_download.content, b"inhoud1")


class EnkelvoudigInformatieObjectPaginationAPITests(JWTAuthMixin, APITestCase):
    list_url = reverse_lazy(EnkelvoudigInformatieObject)
    heeft_alle_autorisaties = True

    def test_pagination_default(self):
        """
        Deleting a Besluit causes all related objects to be deleted as well.
        """
        EnkelvoudigInformatieObjectFactory.create_batch(2)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        EnkelvoudigInformatieObjectFactory.create_batch(2)

        response = self.client.get(self.list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_pagesize_param(self):
        EnkelvoudigInformatieObjectFactory.create_batch(10)

        response = self.client.get(self.list_url, {"pageSize": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["count"], 10)
        self.assertEqual(
            data["next"], f"http://testserver{self.list_url}?page=2&pageSize=5"
        )


@tag("external-urls")
@temp_private_root()
@override_settings(ALLOWED_HOSTS=["testserver"])
class InformatieobjectCreateExternalURLsTests(
    MockSchemasMixin, JWTAuthMixin, APITestCase
):
    heeft_alle_autorisaties = True
    list_url = reverse_lazy(EnkelvoudigInformatieObject)
    mocker_attr = "requests_mock"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            api_root="https://externe.catalogus.nl/api/v1/", api_type=APITypes.ztc
        )

    def setUp(self):
        self.requests_mock = requests_mock.Mocker()
        self.requests_mock.start()
        self.addCleanup(self.requests_mock.stop)

        super().setUp()

    def test_create_external_informatieobjecttype(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        informatieobjecttype = (
            "https://externe.catalogus.nl/api/v1/informatieobjecttypen/"
            "b71f72ef-198d-44d8-af64-ae1932df830a"
        )
        self.requests_mock.get(
            informatieobjecttype,
            json=get_informatieobjecttype_response(catalogus, informatieobjecttype),
        )
        self.requests_mock.get(
            catalogus,
            json=get_catalogus_response(catalogus, informatieobjecttype),
        )

        response = self.client.post(
            self.list_url,
            {
                "identificatie": "12345",
                "bronorganisatie": "159351741",
                "creatiedatum": "2018-06-27",
                "titel": "detailed summary",
                "auteur": "test_auteur",
                "formaat": "txt",
                "taal": "eng",
                "bestandsnaam": "dummy.txt",
                "inhoud": b64encode(b"some file content").decode("utf-8"),
                "link": "http://een.link",
                "beschrijving": "test_beschrijving",
                "informatieobjecttype": informatieobjecttype,
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_create_external_informatieobjecttype_fail_bad_url(self):
        response = self.client.post(
            self.list_url,
            {
                "identificatie": "12345",
                "bronorganisatie": "159351741",
                "creatiedatum": "2018-06-27",
                "titel": "detailed summary",
                "auteur": "test_auteur",
                "formaat": "txt",
                "taal": "eng",
                "bestandsnaam": "dummy.txt",
                "inhoud": b64encode(b"some file content").decode("utf-8"),
                "link": "http://een.link",
                "beschrijving": "test_beschrijving",
                "informatieobjecttype": "abcd",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobjecttype")
        self.assertEqual(error["code"], "bad-url")

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_create_external_informatieobjecttype_fail_not_json_url(self):
        ServiceFactory.create(
            api_root="http://example.com/",
            api_type=APITypes.ztc,
        )
        self.requests_mock.get(
            "http://example.com/", status_code=200, text="<html></html>"
        )

        response = self.client.post(
            self.list_url,
            {
                "identificatie": "12345",
                "bronorganisatie": "159351741",
                "creatiedatum": "2018-06-27",
                "titel": "detailed summary",
                "auteur": "test_auteur",
                "formaat": "txt",
                "taal": "eng",
                "bestandsnaam": "dummy.txt",
                "inhoud": b64encode(b"some file content").decode("utf-8"),
                "link": "http://een.link",
                "beschrijving": "test_beschrijving",
                "informatieobjecttype": "http://example.com/",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobjecttype")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_informatieobjecttype_fail_invalid_schema(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        informatieobjecttype = (
            "https://externe.catalogus.nl/api/v1/informatieobjecttypen/"
            "b71f72ef-198d-44d8-af64-ae1932df830a"
        )
        self.requests_mock.get(
            informatieobjecttype,
            json={
                "url": informatieobjecttype,
                "catalogus": catalogus,
            },
        )
        self.requests_mock.get(
            catalogus,
            json=get_catalogus_response(catalogus, informatieobjecttype),
        )

        response = self.client.post(
            self.list_url,
            {
                "identificatie": "12345",
                "bronorganisatie": "159351741",
                "creatiedatum": "2018-06-27",
                "titel": "detailed summary",
                "auteur": "test_auteur",
                "formaat": "txt",
                "taal": "eng",
                "bestandsnaam": "dummy.txt",
                "inhoud": b64encode(b"some file content").decode("utf-8"),
                "link": "http://een.link",
                "beschrijving": "test_beschrijving",
                "informatieobjecttype": informatieobjecttype,
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobjecttype")
        self.assertEqual(error["code"], "invalid-resource")

    def test_create_external_informatieobjecttype_fail_non_pulish(self):
        catalogus = "https://externe.catalogus.nl/api/v1/catalogussen/1c8e36be-338c-4c07-ac5e-1adf55bec04a"
        informatieobjecttype = (
            "https://externe.catalogus.nl/api/v1/informatieobjecttypen/"
            "b71f72ef-198d-44d8-af64-ae1932df830a"
        )
        informatieobjecttype_data = get_informatieobjecttype_response(
            catalogus, informatieobjecttype
        )
        informatieobjecttype_data["concept"] = True

        self.requests_mock.get(informatieobjecttype, json=informatieobjecttype_data)
        self.requests_mock.get(
            catalogus, json=get_catalogus_response(catalogus, informatieobjecttype)
        )

        response = self.client.post(
            self.list_url,
            {
                "identificatie": "12345",
                "bronorganisatie": "159351741",
                "creatiedatum": "2018-06-27",
                "titel": "detailed summary",
                "auteur": "test_auteur",
                "formaat": "txt",
                "taal": "eng",
                "bestandsnaam": "dummy.txt",
                "inhoud": b64encode(b"some file content").decode("utf-8"),
                "link": "http://een.link",
                "beschrijving": "test_beschrijving",
                "informatieobjecttype": informatieobjecttype,
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "informatieobjecttype")
        self.assertEqual(error["code"], "not-published")


class EIOFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    url = reverse_lazy(EnkelvoudigInformatieObject)

    def test_list_expand(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        eio_data = self.client.get(reverse(eio)).json()
        iotype_data = self.client.get(reverse(eio.informatieobjecttype)).json()

        response = self.client.get(
            self.url,
            {"expand": "informatieobjecttype"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        expected_results = [
            {**eio_data, "_expand": {"informatieobjecttype": iotype_data}}
        ]
        self.assertEqual(data, expected_results)

    def test_retrieve_expand(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        url = reverse(eio)

        eio_data = self.client.get(reverse(eio)).json()
        iotype_data = self.client.get(reverse(eio.informatieobjecttype)).json()

        response = self.client.get(
            url,
            {"expand": "informatieobjecttype"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        expected_results = {
            **eio_data,
            "_expand": {"informatieobjecttype": iotype_data},
        }

        self.assertEqual(data, expected_results)

    def test_trefwoorden(self):
        eio = EnkelvoudigInformatieObjectFactory.create(trefwoorden=["some", "other"])
        EnkelvoudigInformatieObjectFactory.create(trefwoorden=[])
        EnkelvoudigInformatieObjectFactory.create(trefwoorden=["dummy"])

        response = self.client.get(self.url, {"trefwoorden": "some"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(eio)}")
