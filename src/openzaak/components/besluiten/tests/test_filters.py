from django.test import tag

from rest_framework import status
from rest_framework.test import APITestCase

from openzaak.components.catalogi.tests.factories import BesluitTypeFactory
from openzaak.components.catalogi.tests.utils import (
    get_operation_url as get_catalogus_operation_url,
)
from openzaak.utils.tests import JWTAuthMixin

from .factories import BesluitFactory
from .utils import get_operation_url


@tag("external-urls")
class ListFilterLocalFKTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_filter_besluittype(self):
        url = get_operation_url("besluit_list")
        type1, type2 = BesluitTypeFactory.create_batch(2)
        BesluitFactory.create_batch(3, besluittype=type1)
        BesluitFactory.create_batch(1, besluittype=type2)
        type1_url = get_catalogus_operation_url("besluittype_read", uuid=type1.uuid)

        response = self.client.get(url, {"besluittype": type1_url})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
