# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings, tag

import requests_mock
from freezegun import freeze_time
from maykin_common.vcr import VCRMixin
from privates.test import temp_private_root

from ...storage import documenten_storage
from ..factories import EnkelvoudigInformatieObjectFactory
from .mixins import AzureBlobStorageMixin


@tag("gh-2217", "azure-storage")
class AzureStorageDefaultAPIVersionTests(AzureBlobStorageMixin, SimpleTestCase):
    @requests_mock.Mocker()
    def test_default_storage_api_version(self, m):
        m.head(
            f"{documenten_storage.client.url}/{settings.AZURE_LOCATION}/some-file.bin"
        )

        documenten_storage.exists("some-file.bin")

        request = m.request_history[0]

        # Requests use the default version as defined in the Azure SDK
        self.assertEqual(request.headers["x-ms-version"], "2025-11-05")


@tag("gh-2217", "azure-storage")
@override_settings(AZURE_CLIENT_OPTIONS={"api_version": "2025-07-05"})
class AzureStorageOverrideAPIVersionTests(AzureBlobStorageMixin, SimpleTestCase):
    @requests_mock.Mocker()
    def test_override_storage_api_version(self, m):
        m.head(
            f"{documenten_storage.client.url}/{settings.AZURE_LOCATION}/some-file2.bin"
        )

        documenten_storage.exists("some-file2.bin")

        request = m.request_history[0]

        # Requests use the explicitly specified version as defined in the Azure SDK
        self.assertEqual(request.headers["x-ms-version"], "2025-07-05")


@temp_private_root()
@freeze_time("2025-12-01T12:00:00")
@tag("gh-2217", "azure-storage")
class AzureStorageTests(VCRMixin, AzureBlobStorageMixin, TestCase):
    def test_auth_use_connection_string(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            inhoud__filename="test_use_connection_string.bin"
        )

        self.assertTrue(documenten_storage.exists(eio.inhoud.name))
        self.assertTrue(documenten_storage.exists(eio.inhoud.file.name))

        request = self.cassette.requests[0]

        self.assertTrue(
            request.headers["Authorization"].startswith("SharedKey devstoreaccount1:")
        )

    def test_eio_file_path_exists(self):
        eio = EnkelvoudigInformatieObjectFactory.create(
            inhoud__filename="test_eio_file_path_exists.bin"
        )

        self.assertTrue(documenten_storage.exists(eio.inhoud.name))
        self.assertTrue(documenten_storage.exists(eio.inhoud.file.name))


@temp_private_root()
@freeze_time("2025-12-01T12:00:00")
@tag("gh-2217", "azure-storage")
class AzureStorageServicePrincipalAuthenticationTests(AzureBlobStorageMixin, TestCase):
    @override_settings(
        AZURE_ACCOUNT_NAME="documentapiblobstorage",
        AZURE_CLIENT_ID="bd0e03ae-0fec-42dc-9e80-f8b4927c807e",
        AZURE_TENANT_ID="c2c836b6-278b-404f-9b17-59fcef81ef1b",
        AZURE_CLIENT_SECRET="super-secret",
    )
    def test_auth_use_service_principal(self):
        """
        Azurite does not support auth via service principal, so instead of VCR we use
        requests_mock for this test instead
        """
        # Make sure settings for service principal are used
        self.reset_storage()

        # Minimal response from an OIDC discovery endpoint to test authentication
        OPENID_CONFIG = {
            "token_endpoint": "https://login.microsoftonline.com/c2c836b6-278b-404f-9b17-59fcef81ef1b/oauth2/v2.0/token",
            "authorization_endpoint": "https://login.microsoftonline.com/c2c836b6-278b-404f-9b17-59fcef81ef1b/oauth2/v2.0/authorize",
        }

        with requests_mock.Mocker() as m:
            m.get(
                "https://login.microsoftonline.com/c2c836b6-278b-404f-9b17-59fcef81ef1b/v2.0/.well-known/openid-configuration",
                json=OPENID_CONFIG,
            )
            m.post(
                "https://login.microsoftonline.com/c2c836b6-278b-404f-9b17-59fcef81ef1b/oauth2/v2.0/token",
                json={"access_token": "some_token", "expires_in": 3600},
            )
            m.put(
                "https://documentapiblobstorage.blob.core.windows.net/openzaak/documenten/uploads/2025/12/test_auth_use_service_principal.bin?timeout=5",
                status_code=201,
            )
            EnkelvoudigInformatieObjectFactory.create(
                inhoud__filename="test_auth_use_service_principal.bin"
            )

            self.assertEqual(len(m.request_history), 3)

            create_blob_request = m.request_history[2]

            # Assert that the token returned by the auth server is used
            self.assertEqual(
                create_blob_request.headers["Authorization"], "Bearer some_token"
            )
