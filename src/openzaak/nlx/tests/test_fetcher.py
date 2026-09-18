# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
"""
Tests for the ``LINK_FETCHER`` used to validate remote (loose-fk) URLs.

Regression tests for https://github.com/open-zaak/open-zaak/issues/2313: when a
:class:`zgw_consumers.models.Service` has (mutual) TLS certificates configured,
those must be used when fetching the URL, so that endpoints requiring a server
and/or client certificate can be validated.
"""

from django.test import TestCase

import requests_mock
from simple_certmanager.test.factories import CertificateFactory
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.nlx import fetcher

API_ROOT = "https://bag.basisregistraties.overheid.nl/api/v1/"
OBJECT_URL = f"{API_ROOT}panden/0344100000011708"


class FetcherTests(TestCase):
    @requests_mock.Mocker()
    def test_no_service_no_certificates(self, m):
        m.get(OBJECT_URL, status_code=200)

        fetcher(OBJECT_URL)

        self.assertIsNone(m.last_request.cert)
        # requests defaults verify to True
        self.assertNotEqual(m.last_request.verify, False)

    @requests_mock.Mocker()
    def test_service_without_certificates(self, m):
        m.get(OBJECT_URL, status_code=200)
        ServiceFactory.create(
            api_root=API_ROOT,
            api_type=APITypes.orc,
            auth_type=AuthTypes.no_auth,
        )

        fetcher(OBJECT_URL)

        self.assertIsNone(m.last_request.cert)

    @requests_mock.Mocker()
    def test_server_certificate_used_as_verify(self, m):
        m.get(OBJECT_URL, status_code=200)
        server_certificate = CertificateFactory.create()
        ServiceFactory.create(
            api_root=API_ROOT,
            api_type=APITypes.orc,
            auth_type=AuthTypes.no_auth,
            server_certificate=server_certificate,
        )

        fetcher(OBJECT_URL)

        self.assertEqual(
            m.last_request.verify, server_certificate.public_certificate.path
        )

    @requests_mock.Mocker()
    def test_client_certificate_with_private_key_used_as_cert(self, m):
        m.get(OBJECT_URL, status_code=200)
        client_certificate = CertificateFactory.create(with_private_key=True)
        ServiceFactory.create(
            api_root=API_ROOT,
            api_type=APITypes.orc,
            auth_type=AuthTypes.no_auth,
            client_certificate=client_certificate,
        )

        fetcher(OBJECT_URL)

        self.assertEqual(
            m.last_request.cert,
            (
                client_certificate.public_certificate.path,
                client_certificate.private_key.path,
            ),
        )

    @requests_mock.Mocker()
    def test_client_certificate_without_private_key_used_as_cert(self, m):
        m.get(OBJECT_URL, status_code=200)
        client_certificate = CertificateFactory.create()
        ServiceFactory.create(
            api_root=API_ROOT,
            api_type=APITypes.orc,
            auth_type=AuthTypes.no_auth,
            client_certificate=client_certificate,
        )

        fetcher(OBJECT_URL)

        self.assertEqual(
            m.last_request.cert, client_certificate.public_certificate.path
        )

    @requests_mock.Mocker()
    def test_explicit_kwargs_take_precedence(self, m):
        m.get(OBJECT_URL, status_code=200)
        server_certificate = CertificateFactory.create()
        client_certificate = CertificateFactory.create(with_private_key=True)
        ServiceFactory.create(
            api_root=API_ROOT,
            api_type=APITypes.orc,
            auth_type=AuthTypes.no_auth,
            server_certificate=server_certificate,
            client_certificate=client_certificate,
        )

        fetcher(OBJECT_URL, verify=False, cert="/some/explicit/path")

        self.assertEqual(m.last_request.verify, False)
        self.assertEqual(m.last_request.cert, "/some/explicit/path")

    @requests_mock.Mocker()
    def test_nlx_rewrite_still_applies(self, m):
        nlx_url = "http://outway.nlx:8443/kadaster/bag/panden/0344100000011708"
        m.get(nlx_url, status_code=200)
        ServiceFactory.create(
            api_root=API_ROOT,
            api_type=APITypes.orc,
            auth_type=AuthTypes.no_auth,
            nlx="http://outway.nlx:8443/kadaster/bag/",
        )

        fetcher(OBJECT_URL)

        self.assertEqual(m.last_request.url, nlx_url)
