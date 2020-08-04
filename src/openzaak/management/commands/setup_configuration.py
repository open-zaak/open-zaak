# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from argparse import RawTextHelpFormatter

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import ComponentTypes
from vng_api_common.models import APICredential, JWTSecret
from vng_api_common.notifications.constants import (
    SCOPE_NOTIFICATIES_CONSUMEREN_LABEL,
    SCOPE_NOTIFICATIES_PUBLICEREN_LABEL,
)
from vng_api_common.notifications.models import NotificationsConfig

from openzaak.components.autorisaties.api.scopes import SCOPE_AUTORISATIES_LEZEN


class Command(BaseCommand):
    help = "Setup the initial necessary configuration"

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            "openzaak_domain",
            help="Specifies the domain for this Open Zaak installation\n"
            "Used to set the Site.domain\n\n"
            "Example: open-zaak.utrecht.nl (without https://www.)",
        )
        parser.add_argument(
            "notifications_api_root",
            help="Specifies the API root for the Notifications API\n"
            "Used to create credentials to connect Open Zaak to Notifications API\n\n"
            "Example: https://open-notificaties.utrecht.nl/api/v1/",
        )
        parser.add_argument(
            "municipality",
            help="Municipality to which this installation belongs\n"
            "Used in client IDs for API credentials\n\n"
            "Example: Utrecht",
        )
        parser.add_argument(
            "openzaak_to_notif_secret",
            help="Secret used for the Application that allows Open Zaak to retrieve notifications\n\n"
            "Example: cuohyKZ3lM2R",
        )
        parser.add_argument(
            "notif_to_openzaak_secret",
            help="Secret used for the Application that allows Notifications API to retrieve authorizations\n\n"
            "Example: FP6oB8N6cMkr",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            openzaak_domain = options["openzaak_domain"]
            notifications_api_root = options["notifications_api_root"]
            municipality = options["municipality"]
            openzaak_to_notif_secret = options["openzaak_to_notif_secret"]
            notif_to_openzaak_secret = options["notif_to_openzaak_secret"]

            # See: https://open-zaak.readthedocs.io/en/latest/installation/configuration.html#setting-the-domain
            site = Site.objects.get_current()
            site.domain = openzaak_domain
            site.name = f"Open Zaak {municipality}"
            site.save()

            # For the steps below, see:
            # https://open-zaak.readthedocs.io/en/latest/installation/configuration.html#open-zaak

            # Step 1
            notif_config = NotificationsConfig.get_solo()
            notif_config.api_root = notifications_api_root
            notif_config.save()

            # Step 2
            if not APICredential.objects.filter(
                api_root=notifications_api_root
            ).exists():
                APICredential.objects.create(
                    api_root=notifications_api_root,
                    label=f"Open Notificaties {municipality}",
                    client_id=f"open-zaak-{municipality.lower()}",
                    secret=openzaak_to_notif_secret,
                    user_id=f"open-zaak-{municipality.lower()}",
                    user_representation=f"Open Zaak {municipality}",
                )

            # Step 3
            notif_api_jwtsecret_ac = JWTSecret.objects.create(
                identifier=f"open-notificaties-{municipality.lower()}",
                secret=notif_to_openzaak_secret,
            )
            notif_api_applicatie_ac = Applicatie.objects.create(
                label=f"Open Notificaties {municipality}",
                client_ids=[notif_api_jwtsecret_ac.identifier],
            )
            Autorisatie.objects.create(
                applicatie=notif_api_applicatie_ac,
                component=ComponentTypes.ac,
                scopes=[SCOPE_AUTORISATIES_LEZEN],
            )

            # Step 4
            openzaak_applicatie_notif = Applicatie.objects.create(
                label=f"Open Zaak {municipality}",
                client_ids=[f"open-zaak-{municipality.lower()}"],
            )
            Autorisatie.objects.create(
                applicatie=openzaak_applicatie_notif,
                component=ComponentTypes.nrc,
                scopes=[
                    SCOPE_NOTIFICATIES_CONSUMEREN_LABEL,
                    SCOPE_NOTIFICATIES_PUBLICEREN_LABEL,
                ],
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Initial configuration for Open Zaak was setup successfully"
                )
            )
        except Exception as e:
            raise CommandError(
                f"Something went wrong while setting up initial configuration: {e}"
            )
