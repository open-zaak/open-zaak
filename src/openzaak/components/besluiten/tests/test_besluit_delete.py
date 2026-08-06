# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from rest_framework import status
from rest_framework.test import APITestCase

from openzaak.tests.utils import JWTAuthMixin
from openzaak.utils.urls import reverse

from ..models import Besluit, BesluitInformatieObject
from .factories import BesluitFactory, BesluitInformatieObjectFactory


class BesluitDeleteTestCase(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    NAMESPACE = "besluiten"

    def test_delete_besluit_cascades_properly(self):
        """
        Deleting a Besluit causes all related objects to be deleted as well.
        """
        besluit = BesluitFactory.create()
        BesluitInformatieObjectFactory.create(besluit=besluit)
        besluit_delete_url = reverse(besluit, namespace=self.NAMESPACE)

        response = self.client.delete(besluit_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )
        self.assertFalse(Besluit.objects.exists())
        self.assertFalse(BesluitInformatieObject.objects.exists())
