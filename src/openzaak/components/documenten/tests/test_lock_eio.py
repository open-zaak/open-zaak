import tempfile
import uuid
from base64 import b64encode

from django.test import override_settings

from openzaak.components.documenten.api.scopes import (
    SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK, SCOPE_DOCUMENTEN_LOCK
)
from openzaak.components.documenten.api.tests.utils import get_operation_url
from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory
)
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, get_validation_errors

INFORMATIEOBJECTTYPE = 'https://example.com/informatieobjecttype/foo'


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(),
                   LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
class EioLockAPITests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_lock_success(self):
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create()
        assert eio.lock == ''
        url = get_operation_url('enkelvoudiginformatieobject_lock', uuid=eio.latest_version.uuid)

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        data = response.json()
        eio.refresh_from_db()

        self.assertEqual(data['lock'], eio.lock)
        self.assertNotEqual(data['lock'], '')

    def test_lock_fail_locked_doc(self):
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create(lock=uuid.uuid4().hex)

        url = get_operation_url('enkelvoudiginformatieobject_lock', uuid=eio.latest_version.uuid)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        error = get_validation_errors(response, 'nonFieldErrors')
        self.assertEqual(error['code'], 'existing-lock')

    def test_update_success(self):
        lock = uuid.uuid4().hex
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create(lock=lock)
        url = get_operation_url('enkelvoudiginformatieobject_update', uuid=eio.latest_version.uuid)

        response = self.client.patch(
            url,
            {'titel': 'changed',
             'lock': lock}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        eio.refresh_from_db()

        self.assertEqual(eio.latest_version.titel, 'changed')

    def test_update_fail_unlocked_doc(self):
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create()
        assert eio.lock == ''

        url = get_operation_url('enkelvoudiginformatieobject_update', uuid=eio.latest_version.uuid)

        response = self.client.patch(url, {'titel': 'changed'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        error = get_validation_errors(response, 'nonFieldErrors')
        self.assertEqual(error['code'], 'unlocked')

    def test_update_fail_wrong_id(self):
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create(lock=uuid.uuid4().hex)

        url = get_operation_url('enkelvoudiginformatieobject_update', uuid=eio.latest_version.uuid)

        response = self.client.patch(
            url,
            {'titel': 'changed',
             'lock': 12345}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        error = get_validation_errors(response, 'nonFieldErrors')
        self.assertEqual(error['code'], 'incorrect-lock-id')

    def test_create_ignores_lock(self):
        url = get_operation_url('enkelvoudiginformatieobject_create')
        data = {
            'identificatie': uuid.uuid4().hex,
            'bronorganisatie': '159351741',
            'creatiedatum': '2018-06-27',
            'titel': 'detailed summary',
            'auteur': 'test_auteur',
            'formaat': 'txt',
            'taal': 'eng',
            'bestandsnaam': 'dummy.txt',
            'inhoud': b64encode(b'some file content').decode('utf-8'),
            'link': 'http://een.link',
            'beschrijving': 'test_beschrijving',
            'informatieobjecttype': 'https://example.com/ztc/api/v1/catalogus/1/informatieobjecttype/1',
            'vertrouwelijkheidaanduiding': 'openbaar',
            'lock': uuid.uuid4().hex
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertNotIn('lock', response.data)


class EioUnlockAPITests(JWTAuthMixin, APITestCase):

    informatieobjecttype = INFORMATIEOBJECTTYPE
    scopes = [SCOPE_DOCUMENTEN_LOCK]

    def test_unlock_success(self):
        lock = uuid.uuid4().hex
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version__informatieobjecttype=INFORMATIEOBJECTTYPE,
            lock=lock
        )
        url = get_operation_url('enkelvoudiginformatieobject_unlock', uuid=eio.latest_version.uuid)

        response = self.client.post(url, {'lock': lock})

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)

        eio.refresh_from_db()

        self.assertEqual(eio.lock, '')

    def test_unlock_fail_incorrect_id(self):
        eio = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version__informatieobjecttype=INFORMATIEOBJECTTYPE,
            lock=uuid.uuid4().hex
        )
        url = get_operation_url('enkelvoudiginformatieobject_unlock', uuid=eio.latest_version.uuid)

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        error = get_validation_errors(response, 'nonFieldErrors')
        self.assertEqual(error['code'], 'incorrect-lock-id')

    def test_unlock_force(self):
        self.autorisatie.scopes = [SCOPE_DOCUMENTEN_GEFORCEERD_UNLOCK]
        self.autorisatie.save()

        eio = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version__informatieobjecttype=INFORMATIEOBJECTTYPE,
            lock=uuid.uuid4().hex
        )
        url = get_operation_url('enkelvoudiginformatieobject_unlock', uuid=eio.latest_version.uuid)

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)

        eio.refresh_from_db()

        self.assertEqual(eio.lock, '')
