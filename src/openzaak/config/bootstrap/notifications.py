# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from dataclasses import dataclass, field
from typing import List

from django.urls import reverse
from django.utils.crypto import get_random_string

import requests
from notifications_api_common.constants import (
    SCOPE_NOTIFICATIES_CONSUMEREN_LABEL,
    SCOPE_NOTIFICATIES_PUBLICEREN_LABEL,
)
from notifications_api_common.models import NotificationsConfig
from vng_api_common.authorizations.models import Applicatie, Autorisatie, ComponentTypes
from vng_api_common.models import JWTSecret
from zds_client import ClientAuth, ClientError
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from openzaak.components.autorisaties.api.scopes import SCOPE_AUTORISATIES_LEZEN
from openzaak.utils import build_absolute_url

from .datastructures import Output
from .exceptions import SelfTestFailure


def generate_jwt_secret(prefix="oz"):
    random_bit = get_random_string(length=20)
    return f"{prefix}-{random_bit}"


@dataclass
class AutorisatiesAPIClientConfiguration:
    """
    Configure the client for Notifications API to consume Autorisaties API.
    """

    org_name: str
    client_id: str
    secret: str
    secret_provided: bool = field(init=False)

    def __post_init__(self):
        self.secret_provided = bool(self.secret)

        if not self.client_id:
            self.client_id = f"notificaties-api-{self.normalized_org_name}"

        if not self.secret:
            self.secret = generate_jwt_secret()

    @property
    def normalized_org_name(self) -> str:
        return self.org_name.lower().replace(" ", "-") or "ac"

    def configure(self) -> List[Output]:
        # check if there's an existing application/secret
        jwt_secret, _ = JWTSecret.objects.get_or_create(
            identifier=self.client_id, defaults={"secret": self.secret},
        )
        if self.secret_provided and jwt_secret.secret != self.secret:
            jwt_secret.secret = self.secret
            jwt_secret.save(update_fields=["secret"])

        # check for the application
        try:
            applicatie = Applicatie.objects.get(client_ids__contains=[self.client_id])
        except Applicatie.DoesNotExist:
            applicatie = Applicatie.objects.create(
                client_ids=[self.client_id],
                label=f"Notificaties API {self.org_name}".strip(),
            )

        # finally, set up the appropriate permission(s)
        ac_permission, _ = Autorisatie.objects.get_or_create(
            applicatie=applicatie,
            component=ComponentTypes.ac,
            defaults={"scopes": [SCOPE_AUTORISATIES_LEZEN]},
        )
        if SCOPE_AUTORISATIES_LEZEN not in ac_permission.scopes:
            ac_permission.scopes.append(SCOPE_AUTORISATIES_LEZEN)
            ac_permission.save(update_fields=["scopes"])

        # Notifications API should subscribe to authorizations channel to invalidate
        # applications/authorization caches
        required_scopes = {
            SCOPE_NOTIFICATIES_PUBLICEREN_LABEL,
            SCOPE_NOTIFICATIES_CONSUMEREN_LABEL,
        }
        nrc_permission, _ = Autorisatie.objects.get_or_create(
            applicatie=applicatie,
            component=ComponentTypes.nrc,
            defaults={"scopes": list(required_scopes)},
        )
        if not required_scopes.issubset(
            (existing_scopes := set(nrc_permission.scopes))
        ):
            nrc_permission.scopes = sorted(required_scopes.union(existing_scopes))
            nrc_permission.save(update_fields=["scopes"])

        return [
            Output(
                id="autorisatiesAPIClientCredentials",
                title="Notificaties API credentials for Open Zaak Autorisaties API",
                data={"client_id": self.client_id, "secret": jwt_secret.secret,},
            )
        ]

    def test_configuration(self) -> List[Output]:
        # self test by listing the applications in the Autorisaties API
        endpoint = reverse("applicatie-list", kwargs={"version": "1"})
        full_url = build_absolute_url(endpoint, request=None)
        auth = ClientAuth(client_id=self.client_id, secret=self.secret)

        try:
            response = requests.get(
                full_url, headers={**auth.credentials(), "Accept": "application/json",}
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SelfTestFailure(
                "Could not list applications from Autorisaties API"
            ) from exc

        return [
            Output(
                id="autorisatiesAPIClientSelfTest",
                title="Autorisaties API client credentials are valid",
                data={"success": True},
            )
        ]


@dataclass
class NotificationsAPIConfiguration:
    """
    Configure the Open Zaak client to publish notifications.

    1. Create application with permissions to publish notifications
    2. Create service for Notifications API
    3. Set up configuration to point to this service
    """

    org_name: str
    uses_autorisaties_api: bool
    api_root: str
    client_id: str
    client_id_provided: bool = field(init=False)
    secret: str
    secret_provided: bool = field(init=False)

    def __post_init__(self):
        self.secret_provided = bool(self.secret)
        self.client_id_provided = bool(self.client_id)

        if not self.api_root.endswith("/"):
            self.api_root = f"{self.api_root}/"

        if not self.client_id:
            self.client_id = f"open-zaak-{self.normalized_org_name}"

        if not self.secret:
            self.secret = generate_jwt_secret()

    @property
    def normalized_org_name(self) -> str:
        return self.org_name.lower().replace(" ", "-") or "ac"

    def configure(self) -> List[Output]:
        org_label = f"Open Zaak {self.org_name}".strip()

        # 1. set up application and permission (to be returned by Autorisaties API)
        if self.uses_autorisaties_api:
            try:
                applicatie = Applicatie.objects.get(
                    client_ids__contains=[self.client_id]
                )
            except Applicatie.DoesNotExist:
                applicatie = Applicatie.objects.create(
                    client_ids=[self.client_id], label=org_label
                )
            required_scopes = {
                SCOPE_NOTIFICATIES_PUBLICEREN_LABEL,
                SCOPE_NOTIFICATIES_CONSUMEREN_LABEL,  # TODO: figure out why this is needed!
            }
            permission, _ = Autorisatie.objects.get_or_create(
                applicatie=applicatie,
                component=ComponentTypes.nrc,
                defaults={"scopes": list(required_scopes)},
            )
            if not required_scopes.issubset(
                (existing_scopes := set(permission.scopes))
            ):
                permission.scopes = sorted(required_scopes.union(existing_scopes))
                permission.save(update_fields=["scopes"])

        # 2. Set up a service and credentials for the notifications API so Open Zaak
        #    can consume it (read: publish notifications)
        service, created = Service.objects.update_or_create(
            api_root=self.api_root,
            defaults={
                "api_type": APITypes.nrc,
                "oas": f"{self.api_root}schema/openapi.yaml",
                "auth_type": AuthTypes.zgw,
            },
        )
        if created:
            # this values should only be set initially, but can be edited in the admin
            # afterwards without any problems
            service.label = "Notificaties API"
            service.secret = self.secret
            service.client_id = self.client_id
            service.user_id = self.client_id
            service.user_representation = org_label
            service.save()
        else:
            update_fields = []
            if self.client_id_provided and service.client_id != self.client_id:
                service.client_id = self.client_id
                update_fields.append("client_id")
            if self.secret_provided and service.secret != self.secret:
                service.secret = self.secret
                update_fields.append("secret")
            if update_fields:
                service.save(update_fields=update_fields)

        # 3. Set up configuration
        config = NotificationsConfig.get_solo()
        if config.notifications_api_service != service:
            config.notifications_api_service = service
            config.save(update_fields=["notifications_api_service"])

        return [
            Output(
                id="notificationsAPIConfiguration",
                title="Notifications API configured",
                data={"client_id": service.client_id, "secret": service.secret,},
            )
        ]

    def test_configuration(self) -> List[Output]:
        # do self-test - check if we can fetch list of kanalen
        service = Service.objects.get(api_root=self.api_root)
        client = service.build_client()
        try:
            channels = client.list("kanaal")
        except (ClientError, requests.RequestException) as exc:
            raise SelfTestFailure(
                "Could not retrieve list of kanalen from Notificaties API."
            ) from exc

        channel_names = [channel["naam"] for channel in channels] or ["(none)"]
        return [
            Output(
                id="notificationsApiChannels",
                title="Channels present in notifications API",
                data={"channels": ", ".join(channel_names)},
            )
        ]
