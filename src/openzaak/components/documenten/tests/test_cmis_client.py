# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import os
from unittest import skipIf

from django.test import override_settings

from drc_cmis.client import CMISClient
from drc_cmis.models import CMISConfig
from drc_cmis.webservice.client import SOAPCMISClient

from openzaak.components.documenten.query.cmis import CMISQuerySet
from openzaak.components.documenten.tests.factories import (
    EnkelvoudigInformatieObjectFactory,
)
from openzaak.utils.mixins import CMISClientMixin
from openzaak.utils.tests import APICMISTestCase


@override_settings(CMIS_ENABLED=True)
class CMISClientTests(APICMISTestCase):
    @skipIf(
        os.getenv("CMIS_BINDING") == "BROWSER", "CMIS WEBSERVICE binding specific test",
    )
    def test_clear_client_after_config_change_webservice(self):
        EnkelvoudigInformatieObjectFactory.create()

        self.assertTrue(isinstance(CMISQuerySet._cmis_client, SOAPCMISClient))
        self.assertIsNone(CMISClientMixin._cmis_client)

        config = CMISConfig.get_solo()
        config.time_zone = "Europe/Amsterdam"
        config.save()

        self.assertIsNone(CMISQuerySet._cmis_client)

    @skipIf(
        os.getenv("CMIS_BINDING") == "WEBSERVICE", "CMIS BROWSER binding specific test",
    )
    def test_clear_client_after_config_change_browser(self):
        EnkelvoudigInformatieObjectFactory.create()

        self.assertTrue(isinstance(CMISQuerySet._cmis_client, CMISClient))
        self.assertIsNone(CMISClientMixin._cmis_client)

        config = CMISConfig.get_solo()
        config.time_zone = "Europe/Amsterdam"
        config.save()

        self.assertIsNone(CMISQuerySet._cmis_client)
