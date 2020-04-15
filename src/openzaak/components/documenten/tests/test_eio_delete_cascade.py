"""
Ref: https://github.com/VNG-Realisatie/gemma-zaken/issues/349
"""
from rest_framework import status
from vng_api_common.tests import get_validation_errors, reverse
import requests_mock

from django.conf import settings

from openzaak.components.besluiten.tests.factories import BesluitInformatieObjectFactory
from openzaak.components.zaken.tests.factories import ZaakInformatieObjectFactory
from openzaak.utils.tests import JWTAuthMixin, APITestCaseCMIS

from ..models import EnkelvoudigInformatieObject, Gebruiksrechten
from .factories import (
    EnkelvoudigInformatieObjectCanonicalFactory,
    EnkelvoudigInformatieObjectFactory,
    GebruiksrechtenFactory,
    GebruiksrechtenCMISFactory,
)
from .utils import get_operation_url, get_eio_response


class US349TestCase(JWTAuthMixin, APITestCaseCMIS):

    heeft_alle_autorisaties = True

    def test_delete_document_cascades_properly(self):
        """
        Deleting a EnkelvoudigInformatieObject causes all related objects to be deleted as well.
        """
        if settings.CMIS_ENABLED:
            eio = EnkelvoudigInformatieObjectFactory.create()
            eio_url = reverse(eio)
            GebruiksrechtenCMISFactory(informatieobject=eio_url)
            eio_uuid = eio.uuid
        else:
            informatieobject = EnkelvoudigInformatieObjectCanonicalFactory.create()
            GebruiksrechtenFactory.create(informatieobject=informatieobject)
            eio_uuid = informatieobject.latest_version.uuid

        informatieobject_delete_url = get_operation_url(
            "enkelvoudiginformatieobject_delete",
            uuid=eio_uuid,
        )

        response = self.client.delete(informatieobject_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.data
        )

        self.assertEqual(EnkelvoudigInformatieObject.objects.all().count(), 0)

        self.assertFalse(Gebruiksrechten.objects.all().exists())

    def test_delete_document_fail_exising_relations_besluit(self):
        if settings.CMIS_ENABLED:
            eio = EnkelvoudigInformatieObjectFactory.create()
            eio_uuid = eio.uuid
            eio_path = reverse(eio)
            eio_url = f"https://external.documenten.nl/{eio_path}"

            with requests_mock.Mocker(real_http=True) as m:
                m.register_uri(
                    "GET",
                    eio_url,
                    json=get_eio_response(eio_path),
                )

                BesluitInformatieObjectFactory.create(informatieobject=eio_url)
        else:
            informatieobject = EnkelvoudigInformatieObjectCanonicalFactory.create()
            eio_uuid = informatieobject.latest_version.uuid
            BesluitInformatieObjectFactory.create(informatieobject=informatieobject)

        informatieobject_delete_url = get_operation_url(
            "enkelvoudiginformatieobject_delete",
            uuid=eio_uuid,
        )

        response = self.client.delete(informatieobject_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "pending-relations")

    def test_delete_document_fail_exising_relations_zaak(self):
        if settings.CMIS_ENABLED:
            eio = EnkelvoudigInformatieObjectFactory.create()
            eio_uuid = eio.uuid
            eio_path = reverse(eio)
            eio_url = f"https://external.documenten.nl/{eio_path}"

            with requests_mock.Mocker(real_http=True) as m:
                m.register_uri(
                    "GET",
                    eio_url,
                    json=get_eio_response(eio_path),
                )

                ZaakInformatieObjectFactory.create(informatieobject=eio_url)
        else:
            informatieobject = EnkelvoudigInformatieObjectCanonicalFactory.create()
            ZaakInformatieObjectFactory.create(informatieobject=informatieobject)
            eio_uuid = informatieobject.latest_version.uuid

        informatieobject_delete_url = get_operation_url(
            "enkelvoudiginformatieobject_delete",
            uuid=eio_uuid,
        )

        response = self.client.delete(informatieobject_delete_url)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "pending-relations")
