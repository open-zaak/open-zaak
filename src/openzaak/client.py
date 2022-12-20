# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Provide utilities to interact with other APIs as a client.
"""
from typing import IO, Dict, Optional

from zds_client.registry import registry
from zgw_consumers.client import UnknownService, ZGWClient
from zgw_consumers.models import Service


def fetch_object(resource: str, url: str) -> dict:
    """
    Fetch a remote object by URL.
    """
    client = Service.get_client(url)
    if not client:
        raise UnknownService(f"{url} API should be added to Service model")
    obj = client.retrieve(resource, url=url)
    return obj


class OpenZaakClient(ZGWClient):
    def __init__(
        self,
        service: str,
        base_path: str = "/api/v1/",
        auth_value: Optional[Dict[str, str]] = None,
        schema_url: str = "",
        schema_file: IO = None,
        client_certificate_path=None,
        client_private_key_path=None,
        server_certificate_path=None,
    ):
        """
        TODO: should be removed after zds_client is bumped to 2.0.0

        This class has been added because ZGWClient doesn't invoke __init__ of its parent class
        this class has been created solely to fix it
        """
        try:
            self._config = registry[service]
        except KeyError:
            raise RuntimeError(
                "Service '{service}' is not known in the client registry. "
                "Did you load the config first through `Client.load_config(path, **manual)`?".format(
                    service=service
                )
            )

        self.service = service
        self.base_path = base_path

        self._base_url = None

        self.auth = self._config.auth

        self.auth_value = auth_value
        self.schema_url = schema_url
        self.schema_file = schema_file
        self.client_certificate_path = client_certificate_path
        self.client_private_key_path = client_private_key_path
        self.server_certificate_path = server_certificate_path

    @property
    def api_root(self) -> str:
        """
        work-around for libs which use new client
        """
        return self.base_url
