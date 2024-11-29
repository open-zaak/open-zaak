# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import json
import os
from unittest import skipIf
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import serializers
from django.test import tag

import requests_mock
from djangorestframework_camel_case.util import camelize
from drc_cmis.client_builder import get_cmis_client
from drc_cmis.models import CMISConfig, UrlMapping
from rest_framework.test import APITestCase, APITransactionTestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from .helpers import can_connect
from .mocks import MockSchemasMixin, get_eio_response

ALFRESCO_BASE_URL = "http://localhost:8082/alfresco/"


def require_cmis(method_or_class):
    """
    Decorates a test case or method as a CMIS test case.

    * if the CMIS host is not available, the test(s) will be skipped
    * the test(s) is/are tagged so you can easily run _only_ the CMIS tests
    """
    parsed = urlparse(ALFRESCO_BASE_URL)
    cmis_available = can_connect(parsed.netloc)
    possibly_skipped = skipIf(not cmis_available, "CMIS host is not available")(
        method_or_class
    )
    tagged = tag("cmis")(possibly_skipped)
    return tagged


class CMISMixin(MockSchemasMixin):
    @classmethod
    def setUpTestData(cls):
        if hasattr(super(), "setUpTestData"):
            super().setUpTestData()

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

        binding = os.getenv("CMIS_BINDING")
        if binding == "WEBSERVICE":
            config = CMISConfig.get_solo()
            config.client_url = f"{ALFRESCO_BASE_URL}cmisws"
            config.binding = "WEBSERVICE"
            config.other_folder_path = "/DRC/"
            config.zaak_folder_path = "/ZRC/{{ zaaktype }}/{{ zaak }}"
            config.save()

            # Configure the main_repo_id
            client = get_cmis_client()
            config.main_repo_id = client.get_main_repo_id()
            config.save()
        elif binding == "BROWSER":
            config = CMISConfig.get_solo()
            config.client_url = (
                f"{ALFRESCO_BASE_URL}api/-default-/public/cmis/versions/1.1/browser"
            )
            config.binding = "BROWSER"
            config.other_folder_path = "/DRC/"
            config.zaak_folder_path = "/ZRC/{{ zaaktype }}/{{ zaak }}/"
            config.save()
        else:
            raise Exception("No CMIS binding specified")

        if settings.CMIS_URL_MAPPING_ENABLED:
            UrlMapping.objects.create(
                long_pattern="http://testserver",
                short_pattern="http://ts",
                config=config,
            )
            UrlMapping.objects.create(
                long_pattern="http://example.com",
                short_pattern="http://ex.com",
                config=config,
            )
            UrlMapping.objects.create(
                long_pattern="http://openzaak.nl",
                short_pattern="http://oz.nl",
                config=config,
            )

        # add local service configuration - required for composite urls
        ServiceFactory.create(api_root="http://testserver/", api_type=APITypes.orc)

    def setUp(self) -> None:
        # real_http=True to let the other calls pass through and use a different mocker
        # in specific tests cases to catch those requests
        self.adapter = requests_mock.Mocker(real_http=True)
        self.adapter.start()

        self.addCleanup(self._cleanup_alfresco)
        self.addCleanup(self.adapter.stop)

        # testserver vs. example.com
        Site.objects.clear_cache()

        super().setUp()

    def _cleanup_alfresco(self) -> None:
        # Removes the created documents from alfresco
        client = get_cmis_client()
        client.delete_cmis_folders_in_base()


class APICMISTestCase(CMISMixin, APITestCase):
    pass


class APICMISTransactionTestCase(CMISMixin, APITransactionTestCase):
    pass


def serialise_eio(eio, eio_url, **overrides):
    serialised_eio = json.loads(
        serializers.serialize(
            "json",
            [eio],
        )
    )[
        0
    ]["fields"]
    serialised_eio = get_eio_response(eio_url, **serialised_eio, **overrides)
    return camelize(serialised_eio)
