# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Test the flow described in https://github.com/VNG-Realisatie/gemma-zaken/issues/39
"""

import base64
import os
from datetime import date
from io import BytesIO
from unittest import expectedFailure
from unittest.mock import patch
from urllib.parse import urlparse
from uuid import UUID

from django.core.files import File
from django.test import override_settings, tag

from freezegun import freeze_time
from maykin_common.vcr import VCRMixin
from privates.test import temp_private_root
from requests.exceptions import RequestException
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import reverse

from openzaak.components.catalogi.tests.factories import InformatieObjectTypeFactory
from openzaak.tests.utils import JWTAuthMixin

from ...models import EnkelvoudigInformatieObject
from ...storage import documenten_storage
from ..factories import (
    EnkelvoudigInformatieObjectFactory,
)
from ..utils import get_operation_url
from .mixins import AzureBlobStorageMixin


@freeze_time("2025-12-01T12:00:00")
@tag("gh-2217", "azure-storage")
@override_settings(SENDFILE_BACKEND="django_sendfile.backends.simple")
@temp_private_root()
class EnkelvoudigInformatieObjectFileAzureBlobStorageTests(
    JWTAuthMixin, AzureBlobStorageMixin, VCRMixin, APITestCase
):
    heeft_alle_autorisaties = True

    def test_create_enkelvoudiginformatieobject(self):
        """
        Registreer een ENKELVOUDIGINFORMATIEOBJECT
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        url = get_operation_url("enkelvoudiginformatieobject_create")
        data = {
            "identificatie": "AMS20180701001",
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-07-01",
            "titel": "text_extra.txt",
            "auteur": "ANONIEM",
            "formaat": "text/plain",
            "taal": "dut",
            "inhoud": base64.b64encode(b"Extra tekst in bijlage").decode("utf-8"),
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
        }

        # Ensure the same UUID is used to make sure the VCR cassette matches
        with patch(
            "openzaak.components.documenten.models._uuid.uuid4",
            return_value=UUID("40959945-eb82-4b44-b48e-4f96fa33f8f7"),
        ):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        eio = EnkelvoudigInformatieObject.objects.get()

        self.assertEqual(eio.identificatie, "AMS20180701001")
        self.assertEqual(eio.creatiedatum, date(2018, 7, 1))

        download_url = urlparse(response.data["inhoud"])

        self.assertEqual(
            download_url.path,
            get_operation_url("enkelvoudiginformatieobject_download", uuid=eio.uuid),
        )
        self.assertTrue(documenten_storage.exists(eio.inhoud.name))

    # Make sure 5xx responses are returned instead of raising the exception
    @patch.dict(os.environ, {"DEBUG": "false"})
    def test_create_enkelvoudiginformatieobject_azure_request_exception(self):
        """
        Registreer een ENKELVOUDIGINFORMATIEOBJECT
        """
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        url = get_operation_url("enkelvoudiginformatieobject_create")
        data = {
            "identificatie": "AMS20180701001",
            "bronorganisatie": "159351741",
            "creatiedatum": "2018-07-01",
            "titel": "text_extra.txt",
            "auteur": "ANONIEM",
            "formaat": "text/plain",
            "taal": "dut",
            "inhoud": base64.b64encode(b"Extra tekst in bijlage").decode("utf-8"),
            "bestandsnaam": "test_create_enkelvoudiginformatieobject_azure_request_exception.bin",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
        }

        with patch(
            "openzaak.components.documenten.models._uuid.uuid4",
            return_value=UUID("b4070cef-4ae3-4de0-8931-efe695d033f2"),
        ):
            with self.vcr_raises(RequestException):
                response = self.client.post(url, data)

        self.assertEqual(
            response.status_code, status.HTTP_502_BAD_GATEWAY, response.data
        )
        self.assertEqual(
            response.data["detail"], "Error occurred while connecting with Azure"
        )
        self.assertFalse(EnkelvoudigInformatieObject.objects.exists())

    def test_read_detail_file(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            inhoud__filename="some-file.bin"
        )
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio.uuid
        )

        response = self.client.get(file_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.getvalue().decode("utf-8"), "some data")

    def test_list_file(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            inhoud__filename="test_list_file.bin"
        )
        list_url = get_operation_url("enkelvoudiginformatieobject_list")

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["results"]
        download_url = urlparse(data[0]["inhoud"])

        self.assertEqual(
            download_url.path,
            get_operation_url("enkelvoudiginformatieobject_download", uuid=eio.uuid),
        )

    # FIXME deleting EIOs via the API currently does not remove the related file from
    # disk
    # See: https://github.com/open-zaak/open-zaak/issues/2274
    @expectedFailure
    def test_delete_eio_deletes_file(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            inhoud=File(BytesIO(b"some data"), name="some-file2.bin"),
        )
        file_url = get_operation_url(
            "enkelvoudiginformatieobject_download", uuid=eio.uuid
        )

        file_path = eio.inhoud.path.split("oz-documenten/")[1]
        # TODO .exists() doesn't work if you prepend LOCATION
        self.assertTrue(documenten_storage.exists(file_path))

        response = self.client.delete(reverse(eio))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(file_url)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(documenten_storage.exists(file_path))
