# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase

from openzaak.utils.tests import JWTAuthMixin

from ..models import Besluit, BesluitInformatieObject
from .factories import BesluitFactory, BesluitInformatieObjectFactory
from .utils import get_operation_url


class BesluitDeleteTestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_delete_besluit_cascades_properly(self):
        """
        Deleting a Besluit causes all related objects to be deleted as well.
        """
        besluit = BesluitFactory.create()
        BesluitInformatieObjectFactory.create(besluit=besluit)
        besluit_delete_url = get_operation_url("besluit_delete", uuid=besluit.uuid)

        response = self.client.delete(besluit_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        self.assertFalse(Besluit.objects.exists())
        self.assertFalse(BesluitInformatieObject.objects.exists())
