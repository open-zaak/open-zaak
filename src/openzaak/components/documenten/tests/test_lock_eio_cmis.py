# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import uuid
from base64 import b64encode

from django.test import override_settings, tag

from rest_framework import status
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin

from ..api.scopes import SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK, SCOPE_DOCUMENTEN_LOCK
from .factories import EnkelvoudigInformatieObjectFactory
from .utils import get_operation_url


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class EioLockAPITests(JWTAuthMixin, APICMISTestCase):

    heeft_alle_autorisaties = True

    def test_lock_success(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        canonical = eio.canonical

        assert canonical.lock == ""

        lock_url = reverse(
            "enkelvoudiginformatieobject-lock", kwargs={"uuid": eio.uuid}
        )

        lock_response = self.client.post(lock_url)
        self.assertEqual(lock_response.status_code, status.HTTP_200_OK)

        data = lock_response.json()

        eio = EnkelvoudigInformatieObject.objects.get(uuid=eio.uuid)
        canonical = eio.canonical

        self.assertEqual(data["lock"], canonical.lock)
        self.assertNotEqual(data["lock"], "")

    def test_lock_fail_locked_doc(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        url = get_operation_url("enkelvoudiginformatieobject_lock", uuid=eio.uuid)
        # 1st lock
        self.client.post(url)
        response_2nd_lock = self.client.post(url)

        self.assertEqual(
            response_2nd_lock.status_code,
            status.HTTP_400_BAD_REQUEST,
            response_2nd_lock.data,
        )

        error = get_validation_errors(response_2nd_lock, "nonFieldErrors")
        self.assertEqual(error["code"], "existing-lock")

    def test_update_success(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        lock_url = get_operation_url("enkelvoudiginformatieobject_lock", uuid=eio.uuid)
        response_lock = self.client.post(lock_url)

        update_url = get_operation_url(
            "enkelvoudiginformatieobject_update", uuid=eio.uuid
        )

        response_update = self.client.patch(
            update_url, {"titel": "changed", "lock": response_lock.data["lock"]}
        )

        self.assertEqual(
            response_update.status_code, status.HTTP_200_OK, response_update.data
        )

        eios = EnkelvoudigInformatieObject.objects.order_by("versie")
        self.assertEqual(eios.count(), 2)  # version 1 and version 2

        eio = eios[1]
        self.assertEqual(eio.titel, "changed")

    def test_update_fail_unlocked_doc(self):
        eio = EnkelvoudigInformatieObjectFactory.create()
        assert eio.canonical.lock == ""

        update_url = get_operation_url(
            "enkelvoudiginformatieobject_update", uuid=eio.uuid
        )

        response_update = self.client.patch(update_url, {"titel": "changed"})

        self.assertEqual(
            response_update.status_code,
            status.HTTP_400_BAD_REQUEST,
            response_update.data,
        )

        error = get_validation_errors(response_update, "nonFieldErrors")
        self.assertEqual(error["code"], "unlocked")

    def test_update_fail_wrong_id(self):
        eio = EnkelvoudigInformatieObjectFactory.create()

        lock_url = get_operation_url("enkelvoudiginformatieobject_lock", uuid=eio.uuid)
        self.client.post(lock_url)

        url = get_operation_url("enkelvoudiginformatieobject_update", uuid=eio.uuid)

        response = self.client.patch(url, {"titel": "changed", "lock": 12345})

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "incorrect-lock-id")

    def test_create_ignores_lock(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        url = get_operation_url("enkelvoudiginformatieobject_create")
        data = {
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
            "lock": uuid.uuid4().hex,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertNotIn("lock", response.data)


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class EioUnlockAPITests(JWTAuthMixin, APICMISTestCase):

    component = ComponentTypes.drc
    scopes = [SCOPE_DOCUMENTEN_LOCK]

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()
        super().setUpTestData()

    def test_unlock_success(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype
        )

        lock_url = get_operation_url("enkelvoudiginformatieobject_lock", uuid=eio.uuid)
        unlock_url = get_operation_url(
            "enkelvoudiginformatieobject_unlock", uuid=eio.uuid
        )

        lock_response = self.client.post(lock_url)

        unlock_content = {"lock": lock_response.data["lock"]}
        unlock_response = self.client.post(unlock_url, unlock_content)
        self.assertEqual(unlock_response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(
            unlock_response.status_code,
            status.HTTP_204_NO_CONTENT,
            unlock_response.data,
        )

        self.assertEqual(eio.canonical.lock, "")

    def test_unlock_fail_incorrect_id(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype
        )

        lock_url = get_operation_url("enkelvoudiginformatieobject_lock", uuid=eio.uuid)
        unlock_url = get_operation_url(
            "enkelvoudiginformatieobject_unlock", uuid=eio.uuid
        )

        self.client.post(lock_url)
        unlock_response = self.client.post(unlock_url)

        self.assertEqual(
            unlock_response.status_code,
            status.HTTP_400_BAD_REQUEST,
            unlock_response.data,
        )

        error = get_validation_errors(unlock_response, "nonFieldErrors")
        self.assertEqual(error["code"], "incorrect-lock-id")

    def test_unlock_force(self):
        self.autorisatie.scopes = [
            SCOPE_DOCUMENTEN_LOCK,
            SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK,
        ]
        self.autorisatie.save()

        eio = EnkelvoudigInformatieObjectFactory.create(
            informatieobjecttype=self.informatieobjecttype,
        )

        lock_url = get_operation_url("enkelvoudiginformatieobject_lock", uuid=eio.uuid)
        unlock_url = get_operation_url(
            "enkelvoudiginformatieobject_unlock", uuid=eio.uuid
        )

        lock_response = self.client.post(lock_url)

        self.assertEqual(
            lock_response.status_code, status.HTTP_200_OK, lock_response.data
        )

        unlock_response = self.client.post(unlock_url, {"force_unlock": "True"})

        self.assertEqual(
            unlock_response.status_code,
            status.HTTP_204_NO_CONTENT,
            unlock_response.data,
        )

        self.assertEqual(eio.canonical.lock, "")
