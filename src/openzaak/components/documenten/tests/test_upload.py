# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import uuid
from base64 import b64encode

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes, VertrouwelijkheidsAanduiding
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.tests.utils import JWTAuthMixin

from ..api.scopes import (
    SCOPE_DOCUMENTEN_AANMAKEN,
    SCOPE_DOCUMENTEN_ALLES_LEZEN,
    SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
    SCOPE_DOCUMENTEN_BIJWERKEN,
    SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK,
    SCOPE_DOCUMENTEN_LOCK,
)
from ..models import EnkelvoudigInformatieObject
from .factories import EnkelvoudigInformatieObjectFactory
from .utils import get_operation_url, split_file


@temp_private_root()
class SmallFileUpload(JWTAuthMixin, APITestCase):
    component = ComponentTypes.drc
    scopes = [
        SCOPE_DOCUMENTEN_LOCK,
        SCOPE_DOCUMENTEN_AANMAKEN,
        SCOPE_DOCUMENTEN_ALLES_LEZEN,
        SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
        SCOPE_DOCUMENTEN_BIJWERKEN,
    ]

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        cls.informatieobjecttype_url = (
            f"http://testserver{reverse(cls.informatieobjecttype)}"
        )

        super().setUpTestData()

    def test_create_eio(self):
        """
        Test the create process of the documents with base64 files

        Input:
        * inhoud - base64 encoded file
        * bestandsomvang > 0 - file size related to the inhoud

        Expected result:
        * document is created without lock
        * file is downloadable via the link
        * bestandsdelen objects are not created
        """
        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": f"{uuid.uuid4().hex}.txt",
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "bestandsomvang": 17,
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": self.informatieobjecttype_url,
            "vertrouwelijkheidaanduiding": "openbaar",
        }
        list_url = reverse(EnkelvoudigInformatieObject)

        response = self.client.post(list_url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        data = response.json()
        eio = EnkelvoudigInformatieObject.objects.get(
            identificatie=content["identificatie"]
        )
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio.uuid
        )

        self.assertEqual(
            eio.vertrouwelijkheidaanduiding, VertrouwelijkheidsAanduiding.openbaar
        )
        self.assertEqual(eio.titel, "detailed summary")
        self.assertEqual(eio.canonical.bestandsdelen.count(), 0)
        self.assertEqual(eio.inhoud.file.read(), b"some file content")
        self.assertEqual(data["inhoud"], f"http://testserver{file_url}?versie=1")
        self.assertEqual(data["locked"], False)

    def test_create_without_file(self):
        """
        Test the create process of the document metadata without a file

        Input:
        * inhoud - None
        * bestandsomvang - None

        Expected result:
        * document is created without lock
        * file link is None
        * bestandsdelen objects are not created
        """
        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": f"{uuid.uuid4().hex}.txt",
            "inhoud": None,
            "bestandsomvang": None,
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": self.informatieobjecttype_url,
            "vertrouwelijkheidaanduiding": "openbaar",
        }
        list_url = reverse(EnkelvoudigInformatieObject)

        response = self.client.post(list_url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        eio = EnkelvoudigInformatieObject.objects.get(
            identificatie=content["identificatie"]
        )

        self.assertEqual(data["inhoud"], None)
        self.assertEqual(eio.bestandsomvang, None)

    def test_create_empty_file(self):
        """
        Test the create process of the document with empty file

        Input:
        * inhoud - None
        * bestandsomvang - 0

        Expected result:
        * document is created without lock
        * file link can be used to download an empty file
        * bestandsdelen objects are not created
        """
        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": f"{uuid.uuid4().hex}.txt",
            "inhoud": None,
            "bestandsomvang": 0,
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": self.informatieobjecttype_url,
            "vertrouwelijkheidaanduiding": "openbaar",
        }
        list_url = reverse(EnkelvoudigInformatieObject)

        response = self.client.post(list_url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        eio = EnkelvoudigInformatieObject.objects.get(
            identificatie=content["identificatie"]
        )
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio.uuid
        )
        full_file_url = f"http://testserver{file_url}?versie=1"

        self.assertEqual(eio.bestandsomvang, 0)
        self.assertEqual(data["inhoud"], full_file_url)

        file_response = self.client.get(full_file_url)

        self.assertEqual(file_response.getvalue(), b"")

    def test_create_without_size(self):
        """
        Test the create process of the documents with base64 files

        Input:
        * inhoud - base64 encoded file
        * bestandsomvang - None

        Expected result:
        * 400 status because the bestandsomvang is not related to the file size
        """

        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": f"{uuid.uuid4().hex}.txt",
            "bestandsomvang": None,
            "inhoud": b64encode(b"some file content").decode("utf-8"),
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": self.informatieobjecttype_url,
            "vertrouwelijkheidaanduiding": "openbaar",
        }
        list_url = reverse(EnkelvoudigInformatieObject)

        response = self.client.post(list_url, content)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "file-size")

    def test_update_eio_metadata(self):
        """
        Test the update process of the document metadata

        Input:
        * lock document
        * updated fields don't include bestandsomvang and inhoud

        Expected result:
        * new version of document created during lock
        * file link has another version
        * file link points to the same file
        * bestandsdelen objects are not created
        """
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
            inhoud__data=b"1234",
            bestandsomvang=4,
        )
        detail_url = reverse(eio)
        lock_url = get_operation_url("enkelvoudiginformatieobject_lock", uuid=eio.uuid)

        # lock
        response_lock = self.client.post(lock_url)
        lock = response_lock.json()["lock"]

        # update metadata
        response = self.client.patch(
            detail_url, {"titel": "another summary", "lock": lock}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        eio_new, eio_old = EnkelvoudigInformatieObject.objects.filter(
            uuid=eio.uuid
        ).order_by("-versie")
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio_new.uuid
        )

        self.assertEqual(data["inhoud"], f"http://testserver{file_url}?versie=2")

        self.assertEqual(eio_new.versie, 2)
        self.assertEqual(eio_new.titel, "another summary")
        self.assertEqual(eio_new.bestandsomvang, 4)
        self.assertEqual(eio_new.canonical.bestandsdelen.count(), 0)
        self.assertEqual(eio_new.inhoud.read(), b"1234")

        self.assertEqual(eio_old.versie, 1)
        self.assertEqual(eio_old.titel, "some titel")
        self.assertEqual(eio_old.bestandsomvang, 4)
        self.assertEqual(eio_old.canonical.bestandsdelen.count(), 0)
        self.assertEqual(eio_old.inhoud.read(), b"1234")

    def test_update_eio_file(self):
        """
        Test the update process of the document file

        Input:
        * lock document
        * update inhoud with another base64 encoded file
        * update bestandsomvang

        Expected result:
        * new version of document created during lock
        * file link has another version
        * file link points to the new file
        * bestandsdelen objects are not created
        """
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype
        )
        detail_url = reverse(eio)
        lock_url = get_operation_url("enkelvoudiginformatieobject_lock", uuid=eio.uuid)

        # lock
        response_lock = self.client.post(lock_url)
        lock = response_lock.json()["lock"]

        # update metadata
        response = self.client.patch(
            detail_url,
            {
                "inhoud": b64encode(b"some other file content").decode("utf-8"),
                "bestandsomvang": 23,
                "lock": lock,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        eio_new = (
            EnkelvoudigInformatieObject.objects.filter(uuid=eio.uuid)
            .order_by("-versie")
            .first()
        )
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio_new.uuid
        )

        self.assertEqual(eio.canonical.bestandsdelen.count(), 0)
        self.assertEqual(data["inhoud"], f"http://testserver{file_url}?versie=2")
        self.assertEqual(eio_new.inhoud.file.read(), b"some other file content")

    def test_update_eio_file_set_empty(self):
        """
        Test the delete the file from the document

        Input:
        * lock document
        * update inhoud - None
        * update bestandsomvang - None

        Expected result:
        * new version of document created during lock
        * file link - None
        * bestandsdelen objects are not created
        """
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype
        )
        detail_url = reverse(eio)
        lock_url = get_operation_url("enkelvoudiginformatieobject_lock", uuid=eio.uuid)

        # lock
        response_lock = self.client.post(lock_url)
        lock = response_lock.json()["lock"]

        # update metadata
        response = self.client.patch(
            detail_url, {"inhoud": None, "bestandsomvang": None, "lock": lock}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        eio_new = (
            EnkelvoudigInformatieObject.objects.filter(uuid=eio.uuid)
            .order_by("-versie")
            .first()
        )

        self.assertEqual(eio.canonical.bestandsdelen.count(), 0)
        self.assertEqual(eio_new.bestandsomvang, None)
        self.assertEqual(data["inhoud"], None)

    def test_update_eio_only_size(self):
        """
        Test the update process of the size metadata

        Input:
        * lock document
        * update bestandsomvang with positive integer

        Expected result:
        * 400 status because the new bestandsomvang is not related to the file size
        """
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype
        )
        detail_url = reverse(eio)
        lock_url = get_operation_url("enkelvoudiginformatieobject_lock", uuid=eio.uuid)

        # lock
        response_lock = self.client.post(lock_url)
        lock = response_lock.json()["lock"]

        # update metadata
        response = self.client.patch(detail_url, {"bestandsomvang": 20, "lock": lock})

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "file-size")

    def test_update_eio_only_file_without_size(self):
        """
        Test the update process of the file without changing file size

        Input:
        * lock document
        * update inhoud with another base64 encoded file

        Expected result:
        * 400 status because the new file size is not related to the bestandsomvang
        """
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype
        )
        detail_url = reverse(eio)
        lock_url = get_operation_url("enkelvoudiginformatieobject_lock", uuid=eio.uuid)

        # lock
        response_lock = self.client.post(lock_url)
        lock = response_lock.json()["lock"]

        # update metadata
        response = self.client.patch(
            detail_url,
            {
                "inhoud": b64encode(b"some other file content").decode("utf-8"),
                "lock": lock,
            },
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "file-size")

    def test_update_eio_put(self):
        """
        Test the full update process of the document

        Input:
        * lock document
        * update inhoud with another base64 encoded file
        * update all other fields

        Expected result:
        * new version of document created during lock
        * file link has another version
        * file link points to the new file
        * bestandsdelen objects are not created
        """
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype
        )
        detail_url = reverse(eio)
        lock_url = get_operation_url("enkelvoudiginformatieobject_lock", uuid=eio.uuid)

        # lock
        response_lock = self.client.post(lock_url)
        lock = response_lock.json()["lock"]

        # get data
        eio_response = self.client.get(detail_url)
        eio_data = eio_response.data

        # update
        eio_data.update(
            {
                "beschrijving": "beschrijving2",
                "inhoud": b64encode(b"aaaaa"),
                "bestandsomvang": 5,
                "lock": lock,
            }
        )

        for i in ["integriteit", "ondertekening"]:
            eio_data.pop(i)

        response = self.client.put(detail_url, eio_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        eio_new = (
            EnkelvoudigInformatieObject.objects.filter(uuid=eio.uuid)
            .order_by("-versie")
            .first()
        )
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio_new.uuid
        )

        self.assertEqual(eio.canonical.bestandsdelen.count(), 0)
        self.assertEqual(data["inhoud"], f"http://testserver{file_url}?versie=2")
        self.assertEqual(eio_new.inhoud.file.read(), b"aaaaa")
        self.assertEqual(eio_new.bestandsomvang, 5)
        self.assertNotEqual(eio.bestandsomvang, eio_new.bestandsomvang)


@temp_private_root()
@override_settings(DOCUMENTEN_UPLOAD_CHUNK_SIZE=10)
class LargeFileAPITests(JWTAuthMixin, APITestCase):
    component = ComponentTypes.drc
    scopes = [
        SCOPE_DOCUMENTEN_LOCK,
        SCOPE_DOCUMENTEN_AANMAKEN,
        SCOPE_DOCUMENTEN_ALLES_LEZEN,
        SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN,
        SCOPE_DOCUMENTEN_BIJWERKEN,
    ]

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        cls.informatieobjecttype_url = (
            f"http://testserver{reverse(cls.informatieobjecttype)}"
        )

        super().setUpTestData()

    def _create_metadata(self):
        self.file_content = SimpleUploadedFile("file.txt", b"filecontentstring")
        content = {
            "identificatie": uuid.uuid4().hex,
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-06-27",
            "titel": "detailed summary",
            "auteur": "test_auteur",
            "formaat": "txt",
            "taal": "eng",
            "bestandsnaam": f"{uuid.uuid4().hex}.txt",
            "bestandsomvang": self.file_content.size,
            "link": "http://een.link",
            "beschrijving": "test_beschrijving",
            "informatieobjecttype": self.informatieobjecttype_url,
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
        }
        list_url = reverse(EnkelvoudigInformatieObject)

        response = self.client.post(list_url, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        self.assertEqual(response.data["inhoud"], None)

        self.eio = EnkelvoudigInformatieObject.objects.get(
            uuid=response.data["url"].split("/")[-1]
        )
        self.canonical = self.eio.canonical
        data = response.json()

        self.assertEqual(
            self.eio.vertrouwelijkheidaanduiding, VertrouwelijkheidsAanduiding.openbaar
        )
        self.assertEqual(self.eio.titel, "detailed summary")
        self.assertEqual(self.eio.inhoud, "")
        self.assertEqual(self.canonical.bestandsdelen.count(), 2)
        self.assertEqual(data["locked"], True)
        self.assertEqual(data["lock"], self.canonical.lock)

        self.bestandsdelen = self.canonical.bestandsdelen.order_by("volgnummer").all()

        for part in self.bestandsdelen:
            self.assertEqual(part.voltooid, False)
            self.assertEqual(part.inhoud, "")
        self.assertEqual(
            self.bestandsdelen[0].omvang, settings.DOCUMENTEN_UPLOAD_CHUNK_SIZE
        )
        self.assertEqual(
            self.bestandsdelen[1].omvang,
            self.file_content.size - settings.DOCUMENTEN_UPLOAD_CHUNK_SIZE,
        )

    def _upload_part_files(self):
        part_files = split_file(
            self.file_content, settings.DOCUMENTEN_UPLOAD_CHUNK_SIZE
        )
        for part in self.bestandsdelen:
            part_url = get_operation_url("bestandsdeel_update", uuid=part.uuid)

            response = self.client.put(
                part_url,
                {"inhoud": part_files.pop(0), "lock": self.canonical.lock},
                format="multipart",
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.json()["lock"], self.canonical.lock)

            part.refresh_from_db()

            self.assertNotEqual(part.inhoud, "")
            self.assertEqual(part.voltooid, True)

    def _unlock(self):
        unlock_url = get_operation_url(
            "enkelvoudiginformatieobject_unlock", uuid=self.eio.uuid
        )

        response = self.client.post(unlock_url, {"lock": self.canonical.lock})

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        self.canonical.refresh_from_db()
        self.eio.refresh_from_db()

        self.assertEqual(self.canonical.bestandsdelen.count(), 0)
        self.assertNotEqual(self.eio.inhoud.path, "")
        self.assertEqual(self.eio.inhoud.size, self.file_content.size)

    def _download_file(self):
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=self.eio.uuid
        )

        response = self.client.get(file_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.getvalue(), b"filecontentstring")

    def test_create_eio_full_process(self):
        """
        Test the create process of the documents with part files

        1. Create document metadata
        Input:
        * inhoud - None
        * bestandsomvang > 0

        Expected result:
        * document is already locked after creation
        * file link is None
        * bestandsdelen objects are created based on the bestandsomvang

        2. Upload part files
        Input:
        * part files which are the result of splitting the initial file
        * lock

        Expected result:
        * for all part files voltooid = True

        3. Unlock document
        Expected result:
        * part files merged into the whole file
        * file link points to this file
        * bestandsdelen objects are deleted

        4. Download file
        Expected result:
        * file is downloadable via the file link
        """

        self._create_metadata()
        self._upload_part_files()
        self._unlock()
        self._download_file()

    def test_upload_part_wrong_size(self):
        """
        Test the upload of the incorrect part file

        Input:
        * part files with the size different from grootte field
        * lock

        Expected result:
        * 400 status because of the difference between expected and actual file sizes
        """
        self._create_metadata()

        # change file size for part file
        part = self.bestandsdelen[0]
        part.omvang = part.omvang + 1
        part.save()

        # upload part file
        part_url = get_operation_url("bestandsdeel_update", uuid=part.uuid)
        part_file = split_file(
            self.file_content, settings.DOCUMENTEN_UPLOAD_CHUNK_SIZE
        )[0]

        response = self.client.put(
            part_url,
            {"inhoud": part_file, "lock": self.canonical.lock},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "file-size")

    def test_upload_part_twice_correct(self):
        """
        Test the upload of the same part file several times

        Input:
        * part file
        * lock

        Expected result:
        * the repeated upload of the same file is permitted. Voltooid = True
        """
        self._create_metadata()
        self._upload_part_files()

        # upload one of parts again
        self.file_content.seek(0)
        part_files = split_file(
            self.file_content, settings.DOCUMENTEN_UPLOAD_CHUNK_SIZE
        )
        part = self.bestandsdelen[0]
        part_url = get_operation_url("bestandsdeel_update", uuid=part.uuid)

        response = self.client.put(
            part_url,
            {"inhoud": part_files[0], "lock": self.canonical.lock},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        part.refresh_from_db()

        self.assertNotEqual(part.inhoud, "")
        self.assertEqual(part.voltooid, True)

    def test_upload_part_without_lock(self):
        """
        Test the upload of the part file without lock

        Input:
        * part file

        Expected result:
        * 400 status
        """
        self._create_metadata()

        # upload one of parts again
        self.file_content.seek(0)
        part_files = split_file(
            self.file_content, settings.DOCUMENTEN_UPLOAD_CHUNK_SIZE
        )
        part = self.bestandsdelen[0]
        part_url = get_operation_url("bestandsdeel_update", uuid=part.uuid)

        response = self.client.put(
            part_url,
            {
                "inhoud": part_files[0],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "lock")
        self.assertEqual(error["code"], "required")

    def test_upload_part_with_incorrect_lock(self):
        """
        Test the upload of the part file without lock

        Input:
        * part file
        * lock (incorrect)

        Expected result:
        * 400 status
        """
        self._create_metadata()

        # upload one of parts again
        self.file_content.seek(0)
        part_files = split_file(
            self.file_content, settings.DOCUMENTEN_UPLOAD_CHUNK_SIZE
        )
        part = self.bestandsdelen[0]
        part_url = get_operation_url("bestandsdeel_update", uuid=part.uuid)

        response = self.client.put(
            part_url,
            {"inhoud": part_files[0], "lock": "12345"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "incorrect-lock-id")

    def test_unlock_without_uploading(self):
        """
        Test the unlock of the document with no part files uploaded

        Input:
        * bestandsomvang of the document > 0
        * bestandsdelen objects are created but not uploaded

        Expected result:
        * 400 status because the expected size of the file > 0
        """
        self._create_metadata()

        # unlock
        unlock_url = get_operation_url(
            "enkelvoudiginformatieobject_unlock", uuid=self.eio.uuid
        )

        response = self.client.post(unlock_url, {"lock": self.canonical.lock})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "file-size")

    def test_unlock_not_finish_upload(self):
        """
        Test the unlock of the document with not all part files uploaded

        Input:
        * bestandsomvang of the document > 0
        * bestandsdelen objects are created, some of them are uploaded

        Expected result:
        * 400 status because the upload of part files is incomplete
        """
        self._create_metadata()

        # unload 1 part of file
        part_file = split_file(
            self.file_content, settings.DOCUMENTEN_UPLOAD_CHUNK_SIZE
        )[0]
        part = self.bestandsdelen[0]
        part_url = get_operation_url("bestandsdeel_update", uuid=part.uuid)

        response = self.client.put(
            part_url,
            {"inhoud": part_file, "lock": self.canonical.lock},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        # unlock
        unlock_url = get_operation_url(
            "enkelvoudiginformatieobject_unlock", uuid=self.eio.uuid
        )

        response = self.client.post(unlock_url, {"lock": self.canonical.lock})

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "incomplete-upload")

    def test_unlock_not_finish_upload_force(self):
        """
        Test the unlock of the document with not all part files uploaded

        Input:
        * bestandsomvang of the document > 0
        * bestandsdelen objects are created, some of them are uploaded
        * client has 'documenten.geforceerd-unlock' scope

        Expected result:
        * document is unlocked
        * all bestandsdelen are deleted
        * bestandsomvang is None
        """
        self.autorisatie.scopes = self.autorisatie.scopes + [
            SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK
        ]
        self.autorisatie.save()
        self._create_metadata()

        # unload 1 part of file
        part_file = split_file(
            self.file_content, settings.DOCUMENTEN_UPLOAD_CHUNK_SIZE
        )[0]
        part = self.bestandsdelen[0]
        part_url = get_operation_url("bestandsdeel_update", uuid=part.uuid)

        response = self.client.put(
            part_url,
            {"inhoud": part_file, "lock": self.canonical.lock},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        # force unlock
        unlock_url = get_operation_url(
            "enkelvoudiginformatieobject_unlock", uuid=self.eio.uuid
        )

        response = self.client.post(unlock_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.eio.refresh_from_db()
        self.canonical.refresh_from_db()

        self.assertEqual(self.eio.bestandsomvang, None)
        self.assertEqual(self.canonical.bestandsdelen.count(), 0)

    def test_update_metadata_without_upload(self):
        """
        Test the update process of the document metadata

        Input:
        * updated fields don't include bestandsomvang and inhoud

        Expected result:
        * new version of document is not created during lock since the object was created with lock
        * bestandsdelen objects are created
        """
        self._create_metadata()

        # update file metadata
        eio_url = get_operation_url(
            "enkelvoudiginformatieobject_read", uuid=self.eio.uuid
        )

        response = self.client.patch(
            eio_url, {"beschrijving": "beschrijving2", "lock": self.canonical.lock}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()
        new_version = self.eio.canonical.latest_version

        self.assertIsNone(data["inhoud"])  # the link to download is None
        self.assertEqual(len(data["bestandsdelen"]), 2)
        self.assertEqual(new_version.beschrijving, "beschrijving2")

    def test_update_metadata_after_unfinished_upload(self):
        """
        Test the update process of the document metadata with some of part files uploaded

        Input:
        * updated fields don't include bestandsomvang and inhoud

        Expected result:
        * bestandsdelen objects are regenerated
        * all uploaded part files are lost
        """
        self._create_metadata()

        # unload 1 part of file
        part_file = split_file(
            self.file_content, settings.DOCUMENTEN_UPLOAD_CHUNK_SIZE
        )[0]
        part = self.bestandsdelen[0]
        part_url = get_operation_url("bestandsdeel_update", uuid=part.uuid)

        response = self.client.put(
            part_url,
            {"inhoud": part_file, "lock": self.canonical.lock},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        part.refresh_from_db()
        self.assertEqual(part.voltooid, True)

        # update metedata
        eio_url = get_operation_url(
            "enkelvoudiginformatieobject_read", uuid=self.eio.uuid
        )

        response = self.client.patch(
            eio_url, {"beschrijving": "beschrijving2", "lock": self.canonical.lock}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.canonical.refresh_from_db()
        part_new = self.canonical.bestandsdelen.order_by("volgnummer").first()

        self.assertEqual(self.canonical.bestandsdelen.count(), 2)
        self.assertEqual(self.canonical.bestandsdelen.all().empty_bestandsdelen, True)
        self.assertEqual(part_new.voltooid, False)

    def test_update_metadata_set_size(self):
        """
        Test the update process of the file size with some of part files uploaded

        Input:
        * bestandsomvang > 0

        Expected result:
        * bestandsdelen objects are regenerated based on the new bestandsomvang
        * all uploaded part files are lost
        """
        self._create_metadata()

        # update file metadata
        eio_url = get_operation_url(
            "enkelvoudiginformatieobject_read", uuid=self.eio.uuid
        )

        response = self.client.patch(
            eio_url, {"bestandsomvang": 45, "lock": self.canonical.lock}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()
        self.canonical.refresh_from_db()
        new_version = self.canonical.latest_version

        self.assertEqual(new_version.bestandsomvang, 45)
        self.assertEqual(self.canonical.bestandsdelen.count(), 5)
        self.assertEqual(data["inhoud"], None)

    def test_update_metadata_set_size_zero(self):
        """
        Test the update process of the file size = 0

        Input:
        * bestandsomvang = 0

        Expected result:
        * bestandsdelen objects are removed
        * empty file is created
        * file link points to this empty file
        """
        self._create_metadata()

        # update file metadata
        eio_url = get_operation_url(
            "enkelvoudiginformatieobject_read", uuid=self.eio.uuid
        )

        response = self.client.patch(
            eio_url, {"bestandsomvang": 0, "lock": self.canonical.lock}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()
        self.canonical.refresh_from_db()
        new_version = self.canonical.latest_version
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=new_version.uuid
        )

        self.assertEqual(new_version.bestandsomvang, 0)
        self.assertEqual(self.canonical.bestandsdelen.count(), 0)
        self.assertEqual(data["inhoud"], f"http://testserver{file_url}?versie=2")

    def test_update_metadata_set_size_null(self):
        """
        Test the remove of file from the document

        Input:
        * bestandsomvang = None

        Expected result:
        * bestandsdelen objects are removed
        * file link is None
        """
        self._create_metadata()

        # update file metadata
        eio_url = get_operation_url(
            "enkelvoudiginformatieobject_read", uuid=self.eio.uuid
        )

        response = self.client.patch(
            eio_url, {"bestandsomvang": None, "lock": self.canonical.lock}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()
        self.canonical.refresh_from_db()
        new_version = self.canonical.latest_version

        self.assertEqual(new_version.bestandsomvang, None)
        self.assertEqual(self.canonical.bestandsdelen.count(), 0)
        self.assertEqual(data["inhoud"], None)
