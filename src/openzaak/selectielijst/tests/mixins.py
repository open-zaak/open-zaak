# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.selectielijst.models import ReferentieLijstConfig


class ReferentieLijstServiceMixin:
    def setUp(self):
        super().setUp()
        config = ReferentieLijstConfig.get_solo()
        Service.objects.update_or_create(
            api_root=config.api_root,
            defaults=dict(
                api_type=APITypes.orc,
                client_id="test",
                secret="test",
                user_id="test",
                user_representation="Test",
            ),
        )
