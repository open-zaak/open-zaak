from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from openzaak.notifications.viewsets import MultipleNotificationMixin


class MultipleNotificationMixinTests(TestCase):
    def test_no_notification_fields(self):
        mixin = MultipleNotificationMixin()

        with self.assertRaises(ImproperlyConfigured):
            mixin.get_kanaal("test")

    @override_settings(NOTIFICATIONS_DISABLED=False)
    def test_status_code(self):
        mixin = MultipleNotificationMixin()

        result = mixin.notify(404, {})

        self.assertIsNone(result)

    @override_settings(
        NOTIFICATIONS_DISABLED=False, NOTIFICATIONS_GUARANTEE_DELIVERY=True
    )
    @patch(
        "notifications_api_common.models.NotificationsConfig.get_client",
        return_value=None,
    )
    def test_no_client(self, mock_get_client):
        mixin = MultipleNotificationMixin()

        with self.assertRaises(RuntimeError):
            mixin.notify(200, {})
