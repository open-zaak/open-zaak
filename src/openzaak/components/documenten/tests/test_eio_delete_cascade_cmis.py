# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/349
"""
from django.conf import settings
from django.test import override_settings, tag

from drc_cmis.models import CMISConfig, UrlMapping
from rest_framework import status
from vng_api_common.tests import get_validation_errors, reverse

from openzaak.components.besluiten.tests.factories import BesluitInformatieObjectFactory
from openzaak.components.zaken.tests.factories import ZaakInformatieObjectFactory
from openzaak.utils.tests import APICMISTestCase, JWTAuthMixin, OioMixin

from ..models import EnkelvoudigInformatieObject, Gebruiksrechten
from .factories import EnkelvoudigInformatieObjectFactory, GebruiksrechtenCMISFactory
from .utils import get_operation_url


@tag("cmis")
@override_settings(CMIS_ENABLED=True)
class US349TestCase(JWTAuthMixin, APICMISTestCase, OioMixin):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        if settings.CMIS_URL_MAPPING_ENABLED:
            config = CMISConfig.objects.get()

            UrlMapping.objects.create(
                long_pattern="https://external.documenten.nl/documenten",
                short_pattern="https://xdoc.nl",
                config=config,
            )

    heeft_alle_autorisaties = True

    def test_delete_document_cascades_properly(self):
        """
        Deleting a EnkelvoudigInformatieObject causes all related objects to be deleted as well.
        """
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_url = f"http://example.com{reverse(eio)}"
        GebruiksrechtenCMISFactory(informatieobject=eio_url)
        eio_uuid = eio.uuid

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
        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_uuid = eio.uuid
        eio_url = eio.get_url()

        self.create_zaak_besluit_services()
        besluit = self.create_besluit()
        BesluitInformatieObjectFactory.create(informatieobject=eio_url, besluit=besluit)

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

        eio = EnkelvoudigInformatieObjectFactory.create()
        eio_uuid = eio.uuid
        eio_url = eio.get_url()

        self.create_zaak_besluit_services()
        zaak = self.create_zaak()
        ZaakInformatieObjectFactory.create(informatieobject=eio_url, zaak=zaak)

        informatieobject_delete_url = get_operation_url(
            "enkelvoudiginformatieobject_delete", uuid=eio_uuid,
        )

        response = self.client.delete(informatieobject_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "pending-relations")
