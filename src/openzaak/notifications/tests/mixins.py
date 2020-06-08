from vng_api_common.notifications.models import NotificationsConfig
from zgw_consumers.models import Service


class NotificationServiceMixin:
    def setUp(self):
        super().setUp()

        config = NotificationsConfig.get_solo()
        Service.objects.create(
            api_type=APITypes.nrc,
            api_root=config.api_root,
            client_id="test",
            secret="test",
            user_id="test",
            user_representation="Test",
        )
