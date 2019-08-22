from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin

from openzaak.components.besluiten.api.tests.utils import get_operation_url
from openzaak.components.besluiten.models import (
    Besluit, BesluitInformatieObject
)
from openzaak.components.besluiten.models.tests.factories import (
    BesluitFactory, BesluitInformatieObjectFactory
)


class BesluitDeleteTestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_delete_besluit_cascades_properly(self):
        """
        Deleting a Besluit causes all related objects to be deleted as well.
        """
        besluit = BesluitFactory.create()
        BesluitInformatieObjectFactory.create(besluit=besluit)
        besluit_delete_url = get_operation_url('besluit_delete', uuid=besluit.uuid)

        response = self.client.delete(besluit_delete_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertFalse(Besluit.objects.exists())
        self.assertFalse(BesluitInformatieObject.objects.exists())
