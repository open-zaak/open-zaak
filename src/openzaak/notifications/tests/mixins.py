# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from notifications_api_common.models import NotificationsConfig
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service


class NotificationsConfigMixin:
    def setUp(self):
        super().setUp()

        config = NotificationsConfig.get_solo()
        Service.objects.update_or_create(
            api_root=config.api_root,
            defaults=dict(
                api_type=APITypes.nrc,
                client_id="test",
                secret="test",
                user_id="test",
                user_representation="Test",
            ),
        )
