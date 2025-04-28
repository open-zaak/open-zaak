# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import requests_mock
from unittest.mock import patch
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from openzaak.selectielijst.models import ReferentieLijstConfig

from . import mock_resource_list, mock_selectielijst_oas_get


class SelectieLijstMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.base = "https://selectielijst.openzaak.nl/api/v1/"
        cls.service = ServiceFactory(
            api_root=cls.base,
            api_type=APITypes.orc,
            label="external selectielijst",
        )

        # there are TransactionTestCases that truncate the DB, so we need to ensure
        # there are available years
        config = ReferentieLijstConfig.get_solo()
        config.default_year = 2020
        config.allowed_years = [2017, 2020]
        config.service = cls.service
        config.save()

    def setUp(self):
        super().setUp()

        patcher = patch(
            "openzaak.selectielijst.api.ReferentieLijstConfig.get_solo",
            return_value=ReferentieLijstConfig(
                default_year=2020,
                allowed_years=[2017, 2020],
                service=self.service,
            ),
        )
        self.mock_get_solo = patcher.start()
        self.addCleanup(patcher.stop)

        mocker = requests_mock.Mocker()
        mocker.start()
        self.addCleanup(mocker.stop)

        mock_selectielijst_oas_get(mocker)

        mock_resource_list(mocker, "procestypen")
        mock_resource_list(mocker, "resultaten")
        self.requests_mocker = mocker


# backwards compatible alias
ReferentieLijstServiceMixin = SelectieLijstMixin
