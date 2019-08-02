"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/349
"""
from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin

from openzaak.components.documenten.api.tests.utils import get_operation_url
from openzaak.components.documenten.api.scopes import SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN
from openzaak.components.documenten.models import EnkelvoudigInformatieObject, Gebruiksrechten
from openzaak.components.documenten.models.tests.factories import (
    EnkelvoudigInformatieObjectCanonicalFactory, GebruiksrechtenFactory
)

INFORMATIEOBJECTTYPE = 'https://example.com/ztc/api/v1/catalogus/1/informatieobjecttype/1'


@override_settings(LINK_FETCHER='vng_api_common.mocks.link_fetcher_200')
class US349TestCase(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_DOCUMENTEN_ALLES_VERWIJDEREN]
    informatieobjecttype = INFORMATIEOBJECTTYPE

    def test_delete_document_cascades_properly(self):
        """
        Deleting a EnkelvoudigInformatieObject causes all related objects to be deleted as well.
        """
        informatieobject = EnkelvoudigInformatieObjectCanonicalFactory.create(
            latest_version__informatieobjecttype=INFORMATIEOBJECTTYPE
        )

        GebruiksrechtenFactory.create(informatieobject=informatieobject)

        informatieobject_delete_url = get_operation_url(
            'enkelvoudiginformatieobject_delete',
            uuid=informatieobject.latest_version.uuid
        )

        response = self.client.delete(informatieobject_delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)

        self.assertEqual(EnkelvoudigInformatieObject.objects.all().count(), 0)

        self.assertFalse(Gebruiksrechten.objects.all().exists())
