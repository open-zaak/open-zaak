# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.core.management.base import BaseCommand, CommandError

from vng_api_common.notifications.kanalen import Kanaal
from vng_api_common.notifications.models import NotificationsConfig


class Command(BaseCommand):
    help = "Send a test notification to verify if notifications are properly configured"

    def handle(self, *args, **options):
        nrc_client = NotificationsConfig.get_client()

        kanaal_name = "test"
        Kanaal(kanaal_name, "test")

        data = {
            "kanaal": kanaal_name,
            "hoofdObject": "https://example.com",
            "resource": "test",
            "resourceUrl": "https://example.com",
            "actie": "create",
            "aanmaakdatum": "2019-01-01T12:00:00Z",
            "kenmerken": {},
        }

        try:
            nrc_client.create("notificaties", data)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Notification successfully sent to {nrc_client.base_url}!"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Something went wrong while sending the notification to {nrc_client.base_url}"
                )
            )
            raise CommandError(e)
