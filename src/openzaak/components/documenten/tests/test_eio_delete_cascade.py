# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/349
"""
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import get_validation_errors

from openzaak.components.besluiten.tests.factories import BesluitInformatieObjectFactory
from openzaak.components.zaken.tests.factories import ZaakInformatieObjectFactory
from openzaak.utils.tests import JWTAuthMixin

from ..models import EnkelvoudigInformatieObject, Gebruiksrechten
from .factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    GebruiksrechtenFactory,
)
from .utils import get_operation_url


class US349TestCase(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    def test_delete_document_cascades_properly(self):
        """
        Deleting a EnkelvoudigInformatieObject causes all related objects to be deleted as well.
        """

        informatieobject = EnkelvoudigInformatieObjectCanonicalFactory.create()
        GebruiksrechtenFactory.create(informatieobject=informatieobject)
        eio_uuid = informatieobject.latest_version.uuid

        informatieobject_delete_url = get_operation_url(
            "enkelvoudiginformatieobject_delete", uuid=eio_uuid,
        )

        response = self.client.delete(informatieobject_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        self.assertEqual(EnkelvoudigInformatieObject.objects.all().count(), 0)

        self.assertFalse(Gebruiksrechten.objects.all().exists())

    def test_delete_document_fail_exising_relations_besluit(self):
        informatieobject = EnkelvoudigInformatieObjectCanonicalFactory.create()
        eio_uuid = informatieobject.latest_version.uuid
        BesluitInformatieObjectFactory.create(informatieobject=informatieobject)

        informatieobject_delete_url = get_operation_url(
            "enkelvoudiginformatieobject_delete", uuid=eio_uuid,
        )

        response = self.client.delete(informatieobject_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "pending-relations")

    def test_delete_document_fail_exising_relations_zaak(self):
        informatieobject = EnkelvoudigInformatieObjectCanonicalFactory.create()
        ZaakInformatieObjectFactory.create(informatieobject=informatieobject)
        eio_uuid = informatieobject.latest_version.uuid

        informatieobject_delete_url = get_operation_url(
            "enkelvoudiginformatieobject_delete", uuid=eio_uuid,
        )

        response = self.client.delete(informatieobject_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "pending-relations")
