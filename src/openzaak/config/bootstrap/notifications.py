# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from django.conf import settings
from django.urls import reverse

import requests
from django_setup_configuration.configuration import BaseConfigurationStep
from django_setup_configuration.exceptions import SelfTestFailed
from notifications_api_common.constants import (
    SCOPE_NOTIFICATIES_CONSUMEREN_LABEL,
    SCOPE_NOTIFICATIES_PUBLICEREN_LABEL,
)
from notifications_api_common.models import NotificationsConfig
from vng_api_common.authorizations.models import Applicatie, Autorisatie, ComponentTypes
from vng_api_common.models import JWTSecret
from zgw_consumers.client import build_client
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.client import ClientError
from openzaak.components.autorisaties.api.scopes import SCOPE_AUTORISATIES_LEZEN
from openzaak.utils import build_absolute_url
from openzaak.utils.auth import generate_jwt


class AuthNotificationStep(BaseConfigurationStep):
    """
    Create an application record for the Notifications API in Open Zaak's autorisaties API.
    This application is required if the Notifications API uses the Open Zaak autorisaties API
    to check permissions of notification publishers/consumers.

    Normal mode doesn't change the secret after its initial creation.
    If the secret is changed, run this command with 'overwrite' flag

    From: https://open-zaak.readthedocs.io/en/stable/installation/config/openzaak_config.html#open-zaak
    (part "The Notificaties API consumes Open Zaak’s Autorisaties API")
    """

    verbose_name = "Notification Autorisaties API Configuration"
    required_settings = ["NOTIF_OPENZAAK_CLIENT_ID", "NOTIF_OPENZAAK_SECRET"]
    enable_setting = "NOTIF_OPENZAAK_CONFIG_ENABLE"

    def is_configured(self) -> bool:
        return (
            JWTSecret.objects.filter(
                identifier=settings.NOTIF_OPENZAAK_CLIENT_ID
            ).exists()
            and Applicatie.objects.filter(
                client_ids__contains=[settings.NOTIF_OPENZAAK_CLIENT_ID]
            ).exists()
        )

    def configure(self) -> None:
        # store client_id and secret
        jwt_secret, created = JWTSecret.objects.get_or_create(
            identifier=settings.NOTIF_OPENZAAK_CLIENT_ID,
            defaults={"secret": settings.NOTIF_OPENZAAK_SECRET},
        )
        if jwt_secret.secret != settings.NOTIF_OPENZAAK_SECRET:
            jwt_secret.secret = settings.NOTIF_OPENZAAK_SECRET
            jwt_secret.save(update_fields=["secret"])

        # check for the application
        try:
            applicatie = Applicatie.objects.get(
                client_ids__contains=[settings.NOTIF_OPENZAAK_CLIENT_ID]
            )
        except Applicatie.DoesNotExist:
            organization = (
                settings.OPENZAAK_ORGANIZATION or settings.NOTIF_OPENZAAK_CLIENT_ID
            )
            applicatie = Applicatie.objects.create(
                client_ids=[settings.NOTIF_OPENZAAK_CLIENT_ID],
                label=f"Notificaties API {organization}".strip(),
            )

        # finally, set up the appropriate permission(s)
        # 1. Notification API should check permission scopes of requests
        ac_permission, _ = Autorisatie.objects.get_or_create(
            applicatie=applicatie,
            component=ComponentTypes.ac,
            defaults={"scopes": [SCOPE_AUTORISATIES_LEZEN]},
        )
        if SCOPE_AUTORISATIES_LEZEN not in ac_permission.scopes:
            ac_permission.scopes.append(SCOPE_AUTORISATIES_LEZEN.label)
            ac_permission.save(update_fields=["scopes"])

        # 2. Notifications API should subscribe to authorizations channel to invalidate
        # applications/authorization caches
        nrc_scopes = {
            SCOPE_NOTIFICATIES_PUBLICEREN_LABEL,
            SCOPE_NOTIFICATIES_CONSUMEREN_LABEL,
        }
        nrc_permission, _ = Autorisatie.objects.get_or_create(
            applicatie=applicatie,
            component=ComponentTypes.nrc,
            defaults={"scopes": list(nrc_scopes)},
        )
        if not nrc_scopes.issubset(existing_scopes := set(nrc_permission.scopes)):
            nrc_permission.scopes = sorted(nrc_scopes.union(existing_scopes))
            nrc_permission.save(update_fields=["scopes"])

    def test_configuration(self) -> None:
        endpoint = reverse("applicatie-list", kwargs={"version": "1"})
        full_url = build_absolute_url(endpoint, request=None)
        token = generate_jwt(
            settings.NOTIF_OPENZAAK_CLIENT_ID,
            settings.NOTIF_OPENZAAK_SECRET,
            settings.NOTIF_OPENZAAK_CLIENT_ID,
            settings.NOTIF_OPENZAAK_CLIENT_ID,
        )

        try:
            response = requests.get(
                full_url, headers={"Authorization": token, "Accept": "application/json"}
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SelfTestFailed(
                f"Could not list applications from Autorisaties API for {settings.NOTIF_OPENZAAK_CLIENT_ID}"
            ) from exc


class NotificationsAPIConfigurationStep(BaseConfigurationStep):
    """
    Configure the Open Zaak client to publish notifications.

    1. Create application with permissions to publish notifications
    2. Create service for Notifications API
    3. Set up configuration to point to this service

    From: https://open-zaak.readthedocs.io/en/stable/installation/config/openzaak_config.html#open-zaak
    (part "Open Zaak consuming the Notificaties API")

    Normal mode doesn't change the secret after its initial creation.
    If the secret is changed, run this command with 'overwrite' flag
    """

    verbose_name = "Notification API Configuration"
    required_settings = [
        "NOTIF_API_ROOT",
        "OPENZAAK_NOTIF_CLIENT_ID",
        "OPENZAAK_NOTIF_SECRET",
    ]
    enable_setting = "OPENZAAK_NOTIF_CONFIG_ENABLE"

    def is_enabled(self) -> bool:
        result = super().is_enabled()

        if result is False:
            return result

        # extra check if notifications are enabled
        return not settings.NOTIFICATIONS_DISABLED

    def is_configured(self) -> bool:
        application = Applicatie.objects.filter(
            client_ids__contains=[settings.OPENZAAK_NOTIF_CLIENT_ID]
        )
        service = Service.objects.filter(api_root=settings.NOTIF_API_ROOT)
        notif_config = NotificationsConfig.get_solo()

        return (
            application.exists()
            and service.exists()
            and bool(notif_config.notifications_api_service)
        )

    def configure(self):
        organization = (
            settings.OPENZAAK_ORGANIZATION or settings.OPENZAAK_NOTIF_CLIENT_ID
        )
        org_label = f"Open Zaak {organization}".strip()

        # 1. set up application and permission (to be returned by Autorisaties API)
        try:
            applicatie = Applicatie.objects.get(
                client_ids__contains=[settings.OPENZAAK_NOTIF_CLIENT_ID]
            )
        except Applicatie.DoesNotExist:
            applicatie = Applicatie.objects.create(
                client_ids=[settings.OPENZAAK_NOTIF_CLIENT_ID], label=org_label
            )

        nrc_scopes = {
            SCOPE_NOTIFICATIES_PUBLICEREN_LABEL,
            SCOPE_NOTIFICATIES_CONSUMEREN_LABEL,
        }
        nrc_permission, _ = Autorisatie.objects.get_or_create(
            applicatie=applicatie,
            component=ComponentTypes.nrc,
            defaults={"scopes": list(nrc_scopes)},
        )
        if not nrc_scopes.issubset(existing_scopes := set(nrc_permission.scopes)):
            nrc_permission.scopes = sorted(nrc_scopes.union(existing_scopes))
            nrc_permission.save(update_fields=["scopes"])

        # 2. Set up a service and credentials for the notifications API so Open Zaak
        #    can consume it (read: publish notifications)
        service, created = Service.objects.update_or_create(
            api_root=settings.NOTIF_API_ROOT,
            defaults={
                "label": "Notificaties API",
                "slug": settings.NOTIF_API_ROOT,
                "api_type": APITypes.nrc,
                "oas": settings.NOTIF_API_OAS,
                "auth_type": AuthTypes.zgw,
                "client_id": settings.OPENZAAK_NOTIF_CLIENT_ID,
                "secret": settings.OPENZAAK_NOTIF_SECRET,
                "user_id": settings.OPENZAAK_NOTIF_CLIENT_ID,
                "user_representation": org_label,
            },
        )
        if not created:
            service.oas = settings.NOTIF_API_OAS
            service.client_id = settings.OPENZAAK_NOTIF_CLIENT_ID
            service.secret = settings.OPENZAAK_NOTIF_SECRET
            service.user_id = settings.OPENZAAK_NOTIF_CLIENT_ID
            service.user_representation = org_label
            service.save()

        # 3. Set up configuration
        config = NotificationsConfig.get_solo()
        if config.notifications_api_service != service:
            config.notifications_api_service = service
            config.save(update_fields=["notifications_api_service"])

    def test_configuration(self):
        """
        fetch kanalen
        """
        # check if we can fetch list of kanalen
        client = build_client(Service.objects.get(api_root=settings.NOTIF_API_ROOT))
        try:
            client.get("kanaal")
        except (ClientError, requests.RequestException) as exc:
            raise SelfTestFailed(
                "Could not retrieve list of kanalen from Notificaties API."
            ) from exc
