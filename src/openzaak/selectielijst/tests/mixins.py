from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.selectielijst.models import ReferentieLijstConfig


class ReferentieLijstServiceMixin:
    def setUp(self):
        super().setUp()
        config = ReferentieLijstConfig.get_solo()
        Service.objects.create(
            api_type=APITypes.orc,
            api_root=config.api_root,
            client_id="test",
            secret="test",
            user_id="test",
            user_representation="Test",
        )
