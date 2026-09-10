# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
import requests
from zgw_consumers.models import Service


def fetcher(url: str, *args, **kwargs):
    """
    Fetch the URL using requests.

    If the NLX address is configured, rewrite absolute url to NLX url.

    If the matching :class:`zgw_consumers.models.Service` has TLS certificates
    configured, use them so that endpoints requiring a server and/or client
    certificate (mutual TLS) can be reached during validation. See #2313.
    """
    service = Service.get_service(url)
    if service:
        if service.nlx:
            # rewrite url
            url = url.replace(service.api_root, service.nlx, 1)

        # apply the (mutual) TLS configuration of the service, mirroring
        # zgw_consumers.client.ServiceConfigAdapter.get_client_session_kwargs
        if "verify" not in kwargs and (server_cert := service.server_certificate):
            kwargs["verify"] = server_cert.public_certificate.path
        if "cert" not in kwargs and (client_cert := service.client_certificate):
            client_cert_path = client_cert.public_certificate.path
            kwargs["cert"] = (
                (client_cert_path, privkey.path)
                if (privkey := client_cert.private_key)
                else client_cert_path
            )

    return requests.get(url, *args, **kwargs)
