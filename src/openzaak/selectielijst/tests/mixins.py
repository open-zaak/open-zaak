# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import requests_mock
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.selectielijst.models import ReferentieLijstConfig

from . import mock_oas_get, mock_resource_list


class SelectieLijstMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # there are TransactionTestCases that truncate the DB, so we need to ensure
        # there are available years
        config = ReferentieLijstConfig.get_solo()
        config.allowed_years = [2017, 2020]
        config.save()
        cls.base = config.api_root

        Service.objects.update_or_create(
            api_root=cls.base,
            defaults=dict(
                api_type=APITypes.orc,
                label="external selectielijst",
                auth_type=AuthTypes.no_auth,
            ),
        )

    def setUp(self):
        super().setUp()

        mocker = requests_mock.Mocker()
        mocker.start()
        self.addCleanup(mocker.stop)

        mock_oas_get(mocker)

        mock_resource_list(mocker, "procestypen")
        mock_resource_list(mocker, "resultaten")
        self.requests_mocker = mocker


# backwards compatible alias
ReferentieLijstServiceMixin = SelectieLijstMixin
