import uuid
from base64 import b64encode

from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import ComponentTypes
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.utils.tests import JWTAuthMixin

from ..api.scopes import SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK, SCOPE_DOCUMENTEN_LOCK
from .factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
)
from .utils import get_operation_url


@temp_private_root()
class EioLockAPITests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_lock_success(self):
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create()
        assert eio.lock == ""
        url = get_operation_url(
            "enkelvoudiginformatieobject_lock", uuid=eio.latest_version.uuid
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()
        eio.refresh_from_db()

        self.assertEqual(data["lock"], eio.lock)
        self.assertNotEqual(data["lock"], "")

    def test_lock_fail_locked_doc(self):
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create(lock=uuid.uuid4().hex)

        url = get_operation_url(
            "enkelvoudiginformatieobject_lock", uuid=eio.latest_version.uuid
        )
        response = self.client.post(url)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "existing-lock")

    def test_update_success(self):
        lock = uuid.uuid4().hex
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create(lock=lock)
        url = get_operation_url(
            "enkelvoudiginformatieobject_update", uuid=eio.latest_version.uuid
        )

        response = self.client.patch(url, {"titel": "changed", "lock": lock})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        eio.refresh_from_db()

        self.assertEqual(eio.latest_version.titel, "changed")

    def test_update_fail_unlocked_doc(self):
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create()
        assert eio.lock == ""

        url = get_operation_url(
            "enkelvoudiginformatieobject_update", uuid=eio.latest_version.uuid
        )

        response = self.client.patch(url, {"titel": "changed"})

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unlocked")

    def test_update_fail_wrong_id(self):
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create(lock=uuid.uuid4().hex)

        url = get_operation_url(
            "enkelvoudiginformatieobject_update", uuid=eio.latest_version.uuid
        )

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


class EioUnlockAPITests(JWTAuthMixin, APITestCase):

    component = ComponentTypes.drc
    scopes = [SCOPE_DOCUMENTEN_LOCK]

    @classmethod
    def setUpTestData(cls):
        cls.informatieobjecttype = InformatieObjectTypeFactory.create()
        super().setUpTestData()

    def test_unlock_success(self):
        lock = uuid.uuid4().hex
        eio = EnkelvoudigInformatieObjectFactory.create(
            canonical__lock=lock, informatieobjecttype=self.informatieobjecttype
        )
        url = get_operation_url("enkelvoudiginformatieobject_unlock", uuid=eio.uuid)

        response = self.client.post(url, {"lock": lock})

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        eio.refresh_from_db()

        self.assertEqual(eio.canonical.lock, "")

    def test_unlock_fail_incorrect_id(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            canonical__lock=uuid.uuid4().hex,
            informatieobjecttype=self.informatieobjecttype,
        )
        url = get_operation_url("enkelvoudiginformatieobject_unlock", uuid=eio.uuid)

        response = self.client.post(url)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "incorrect-lock-id")

    def test_unlock_force(self):
        self.autorisatie.scopes = [SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK]
        self.autorisatie.save()

        eio = EnkelvoudigInformatieObjectFactory.create(
            canonical__lock=uuid.uuid4().hex,
            informatieobjecttype=self.informatieobjecttype,
        )
        url = get_operation_url("enkelvoudiginformatieobject_unlock", uuid=eio.uuid)

        response = self.client.post(url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        eio.refresh_from_db()

        self.assertEqual(eio.canonical.lock, "")
