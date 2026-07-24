# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact

from openzaak.tests.utils import TestMigrations


class TestFailedNotificationMigration(TestMigrations):
    migrate_from = "0004_alter_failednotification_status_code"
    migrate_to = "0005_migrate_failednotifications"
    app = "notifications_log"

    def setUpBeforeMigration(self, apps):
        self.OldFailedNotification = apps.get_model(
            "notifications_log", "FailedNotification"
        )
        self.NewFailedNotification = apps.get_model(
            "notifications_api_common", "FailedNotification"
        )
        self.NotificationResponse = apps.get_model(
            "notifications_api_common", "NotificationResponse"
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

        # No status_code
        self.OldFailedNotification.objects.create(
            logger_name="notifications_api_common.tasks",
            level=30,  # WARNING
            msg="Failed to send notification",
            trace="Exception line 12312124810284124",
            message=self.message,
        )

        # with status_code
        self.OldFailedNotification.objects.create(
            logger_name="notifications_api_common.tasks",
            level=30,  # WARNING
            msg="Failed to send notification",
            status_code=403,
            message=self.message,
        )

        # long msg
        self.OldFailedNotification.objects.create(
            logger_name="notifications_api_common.tasks",
            level=30,  # WARNING
            msg="a" * 1000,
            status_code=500,
            message=self.message,
        )

    def test_failed_notification_migrated_to_base_notification(self):
        self.assertEqual(self.OldFailedNotification.objects.count(), 0)
        self.assertEqual(self.NewFailedNotification.objects.count(), 3)
        self.assertEqual(self.NotificationResponse.objects.count(), 3)

        nr_none = self.NotificationResponse.objects.get(response_status=None)
        self.assertEqual(nr_none.exception, "Failed to send notification")
        self.assertEqual(nr_none.failed_notification.type, "notification")
        self.assertEqual(nr_none.failed_notification.message, self.message)

        nr_403 = self.NotificationResponse.objects.get(response_status=403)
        self.assertEqual(nr_403.exception, "Failed to send notification")
        self.assertEqual(nr_403.failed_notification.type, "notification")
        self.assertEqual(nr_403.failed_notification.message, self.message)

        nr_long = self.NotificationResponse.objects.get(response_status=500)
        self.assertEqual(nr_long.exception, "a" * 500)
        self.assertEqual(nr_long.failed_notification.type, "notification")
        self.assertEqual(nr_long.failed_notification.message, self.message)
