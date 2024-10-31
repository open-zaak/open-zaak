# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import requests_mock
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.selectielijst.models import ReferentieLijstConfig

from . import mock_resource_list, mock_selectielijst_oas_get


class SelectieLijstMixin:
    # @classmethod
    # def setUpTestData(cls):
    #     super().setUpTestData()

    #     # there are TransactionTestCases that truncate the DB, so we need to ensure
    #     # there are available years
    #     config = ReferentieLijstConfig.get_solo()
    #     config.default_year = 2020
    #     config.allowed_years = [2017, 2020]
    #     config.save()
    #     cls.base = config.api_root

    #     Service.objects.update_or_create(
    #         api_root=cls.base,
    #         defaults=dict(
    #             api_type=APITypes.orc,
    #             label="external selectielijst",
    #             auth_type=AuthTypes.no_auth,
    #         ),
    #     )

    def setUp(self):
        super().setUp()

        # TODO somehow fix this without adding it to setUp
        self.base = "https://selectielijst.openzaak.nl/api/v1/"
        service, _ = Service.objects.update_or_create(
            api_root=self.base,
            defaults=dict(
                slug=self.base,
                api_type=APITypes.orc,
                label="external selectielijst",
                auth_type=AuthTypes.no_auth,
            ),
        )

        # there are TransactionTestCases that truncate the DB, so we need to ensure
        # there are available years
        config = ReferentieLijstConfig.get_solo()
        config.default_year = 2020
        config.allowed_years = [2017, 2020]
        config.service = service
        config.save()

        mocker = requests_mock.Mocker()
        mocker.start()
        self.addCleanup(mocker.stop)

        mock_selectielijst_oas_get(mocker)

        mock_resource_list(mocker, "procestypen")
        mock_resource_list(mocker, "resultaten")
        self.requests_mocker = mocker


# backwards compatible alias
ReferentieLijstServiceMixin = SelectieLijstMixin
