# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.conf import settings
from django.urls import reverse

import requests
from django_setup_configuration.configuration import BaseConfigurationStep
from django_setup_configuration.exceptions import SelfTestFailed
from vng_api_common.authorizations.models import Applicatie
from vng_api_common.models import JWTSecret

from openzaak.utils import build_absolute_url
from openzaak.utils.auth import generate_jwt


class DemoUserStep(BaseConfigurationStep):
    """
    Create demo user to request Open Zaak APIs

    **NOTE** For now demo user has all permissions.

    Normal mode doesn't change the secret after its initial creation.
    Run this command with the 'overwrite' flag to change the secret
    """

    # todo load permissions with yaml file and env var?

    verbose_name = "Demo User Configuration"
    required_settings = ["DEMO_CLIENT_ID", "DEMO_SECRET", "OPENZAAK_DOMAIN"]
    enable_setting = "DEMO_CONFIG_ENABLE"

    def is_configured(self) -> bool:
        return (
            JWTSecret.objects.filter(identifier=settings.DEMO_CLIENT_ID).exists()
            and Applicatie.objects.filter(
                client_ids__contains=[settings.DEMO_CLIENT_ID]
            ).exists()
        )

    def configure(self) -> None:
        # store client_id and secret
        jwt_secret, created = JWTSecret.objects.get_or_create(
            identifier=settings.DEMO_CLIENT_ID,
            defaults={"secret": settings.DEMO_SECRET},
        )
        if jwt_secret.secret != settings.DEMO_SECRET:
            jwt_secret.secret = settings.DEMO_SECRET
            jwt_secret.save(update_fields=["secret"])

        # check for the application
        try:
            Applicatie.objects.get(client_ids__contains=[settings.DEMO_CLIENT_ID])
        except Applicatie.DoesNotExist:
            Applicatie.objects.create(
                client_ids=[settings.DEMO_CLIENT_ID],
                label="Demo user",
                heeft_alle_autorisaties=True,
            )

    def test_configuration(self) -> None:
        endpoint = reverse("zaak-list", kwargs={"version": "1"})
        full_url = build_absolute_url(endpoint, request=None)
        token = generate_jwt(
            settings.DEMO_CLIENT_ID,
            settings.DEMO_SECRET,
            settings.DEMO_CLIENT_ID,
            settings.DEMO_CLIENT_ID,
        )

        try:
            response = requests.get(
                full_url,
                headers={
                    "Authorization": token,
                    "Accept": "application/json",
                    "Accept-Crs": "EPSG:4326",
                },
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SelfTestFailed(
                f"Could not list zaken for {settings.DEMO_CLIENT_ID}"
            ) from exc
