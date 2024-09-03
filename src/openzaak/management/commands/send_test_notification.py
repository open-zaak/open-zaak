# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact

from django.core.management import BaseCommand, CommandError, call_command

from notifications_api_common.kanalen import Kanaal
from notifications_api_common.models import NotificationsConfig
from zgw_consumers.client import build_client

TEST_CHANNEL_NAME = "test"


class Command(BaseCommand):
    help = "Send a test notification to verify if notifications are properly configured"

    def handle(self, **options):
        nrc_config = NotificationsConfig.get_solo()
        if not nrc_config.notifications_api_service:
            raise CommandError(
                "Notifications are not properly configured. Please configure "
                "them via the admin interface or the ``setup_configuration`` command."
            )

        nrc_client = build_client(nrc_config.notifications_api_service)
        if not nrc_client:
            raise CommandError(
                "Notifications are not properly configured. Please configure "
                "them via the admin interface or the ``setup_configuration`` command."
            )

        # ensure it's in the channel registry and the test channel exists
        Kanaal(TEST_CHANNEL_NAME, "test")
        call_command(
            "register_kanalen",
            kanalen=[TEST_CHANNEL_NAME],
            stdout=self.stdout,
            stderr=self.stderr,
        )

        data = {
            "kanaal": TEST_CHANNEL_NAME,
            "hoofdObject": "https://example.com",
            "resource": "test",
            "resourceUrl": "https://example.com",
            "actie": "create",
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "kenmerken": {},
        }

        try:
            nrc_client.request(url="notificaties", method="POST", data=data)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Notification successfully sent to {nrc_client.base_url}"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Something went wrong while sending the notification to {nrc_client.base_url}"
                )
            )
            raise CommandError(e)
