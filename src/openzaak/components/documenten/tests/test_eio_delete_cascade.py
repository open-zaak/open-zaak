"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/349
"""
from openzaak.components.besluiten.models.tests.factories import (
    BesluitInformatieObjectFactory
)
from openzaak.components.documenten.api.tests.utils import get_operation_url
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject, Gebruiksrechten
)
from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory, GebruiksrechtenFactory
)
from openzaak.components.zaken.models.tests.factories import (
    ZaakInformatieObjectFactory
)
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, get_validation_errors


class US349TestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_delete_document_cascades_properly(self):
        """
        Deleting a EnkelvoudigInformatieObject causes all related objects to be deleted as well.
        """
        informatieobject = EnkelvoudigInformatieObjectCanonicalFactory.create()

        GebruiksrechtenFactory.create(informatieobject=informatieobject)

        informatieobject_delete_url = get_operation_url(
            'enkelvoudiginformatieobject_delete',
            uuid=informatieobject.latest_version.uuid
        )

        response = self.client.delete(informatieobject_delete_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)

        self.assertEqual(EnkelvoudigInformatieObject.objects.all().count(), 0)

        self.assertFalse(Gebruiksrechten.objects.all().exists())

    def test_delete_document_fail_exising_relations_besluit(self):
        informatieobject = EnkelvoudigInformatieObjectCanonicalFactory.create()
        BesluitInformatieObjectFactory.create(informatieobject=informatieobject)

        informatieobject_delete_url = get_operation_url(
            'enkelvoudiginformatieobject_delete',
            uuid=informatieobject.latest_version.uuid
        )

        response = self.client.delete(informatieobject_delete_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        error = get_validation_errors(response, 'nonFieldErrors')
        self.assertEqual(error['code'], 'pending-relations')

    def test_delete_document_fail_exising_relations_zaak(self):
        informatieobject = EnkelvoudigInformatieObjectCanonicalFactory.create()
        ZaakInformatieObjectFactory.create(informatieobject=informatieobject)

        informatieobject_delete_url = get_operation_url(
            'enkelvoudiginformatieobject_delete',
            uuid=informatieobject.latest_version.uuid
        )

        response = self.client.delete(informatieobject_delete_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        error = get_validation_errors(response, 'nonFieldErrors')
        self.assertEqual(error['code'], 'pending-relations')
