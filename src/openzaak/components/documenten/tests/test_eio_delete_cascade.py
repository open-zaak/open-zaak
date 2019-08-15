"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/349
"""
from openzaak.components.documenten.api.tests.utils import get_operation_url
from openzaak.components.documenten.models import (
    EnkelvoudigInformatieObject, Gebruiksrechten
)
from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory, GebruiksrechtenFactory
)
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin


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
