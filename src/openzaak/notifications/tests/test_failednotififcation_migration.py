from notifications_api_common.models import BaseNotification

from openzaak.tests.utils import TestMigrations


class TestFailedNotificationMigration(TestMigrations):
    migrate_from = "0004_alter_failednotification_status_code"
    migrate_to = "0005_migrate_failednotifications"
    app = "notifications_log"

    def setUpBeforeMigration(self, apps):
        self.FailedNotification = apps.get_model(
            "notifications_log", "FailedNotification"
        )
        self.BaseNotification = apps.get_model(
            "notifications_api_common", "BaseNotification"
        )

        self.message = {
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "actie": "create",
            "hoofdObject": "http://testserver/foo",
            "kanaal": "zaken",
            "kenmerken": {},
            "resource": "zaak",
            "resourceUrl": "http://testserver/foo",
        }

        self.FailedNotification.objects.create(
            logger_name="notifications_api_common.tasks",
            level=30,  # WARNING
            msg="Failed to send notification",
            trace="Exception line 12312124810284124",
            message=self.message,
        )

    def test_failed_notification_migrated_to_base_notification(self):
        self.assertEqual(self.FailedNotification.objects.count(), 0)
        self.assertEqual(self.BaseNotification.objects.count(), 1)

        bn = BaseNotification.objects.get()
        self.assertEqual(bn.type, "notification")
        self.assertEqual(bn.message, self.message)
