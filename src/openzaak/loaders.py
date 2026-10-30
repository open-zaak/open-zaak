# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import json
from inspect import getmembers
from typing import Any, Dict

from django.db import models
from django.db.models.base import ModelBase

import requests
import structlog
from ape_pie import APIClient
from django_loose_fk.loaders import BaseLoader, FetchError, FetchJsonError
from django_loose_fk.virtual_models import virtual_model_factory
from djangorestframework_camel_case.util import underscoreize
from vng_api_common.descriptors import GegevensGroepType
from vng_api_common.geo import DEFAULT_CRS, HEADER_ACCEPT

from openzaak.utils.snapshot import JSON, ETag, NotModified, Ok, fetch

logger = structlog.stdlib.get_logger(__name__)


def get_service_client(url: str) -> APIClient:
    """
    A client configured from the ``Service`` that ``url`` belongs to: auth, mTLS,
    timeout and NLX. Without such a service, an unauthenticated client, as before.
    """
    from zgw_consumers.client import build_client
    from zgw_consumers.models import Service

    if service := Service.get_service(url):
        client = build_client(service)
    else:
        logger.warning("no_service_found_for_url", url=url)
        client = APIClient(url)

    # a Zaken API answers 412 without it on resources with geo fields; others ignore it
    client.headers[HEADER_ACCEPT] = DEFAULT_CRS
    return client


def get_from_service(url: str, /, *, if_none_match: ETag | None) -> Ok | NotModified:
    """
    The ``Transport`` for :func:`openzaak.utils.snapshot.fetch`.
    """
    headers = {} if if_none_match is None else {"If-None-Match": if_none_match}

    try:
        with get_service_client(url) as client:
            response = client.get(url, headers=headers)
    except requests.exceptions.RequestException as exc:
        raise FetchError(exc.args[0]) from exc

    # only when asked: a 304 without an entry to fall back on has no body to parse
    if if_none_match is not None and response.status_code == 304:
        return NotModified()

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise FetchError(exc.args[0]) from exc

    try:
        data: JSON = response.json()
    except json.JSONDecodeError as exc:
        raise FetchJsonError(exc.args[0]) from exc

    return Ok(etag=response.headers.get("ETag"), body=data)


class AuthorizedRequestsLoader(BaseLoader):
    """
    Fetch external API objects with Authorization header.

    Within a :func:`openzaak.utils.snapshot.snapshot_scope`, repeated fetches of a
    URL are served from the scope's snapshot.
    """

    @staticmethod
    def fetch_object(url: str, do_underscoreize=True) -> dict:
        data = fetch(get_from_service, url)
        if not isinstance(data, dict):
            raise FetchJsonError(f"Expected a JSON object from {url}")

        if not do_underscoreize:
            return data

        return underscoreize(data)

    def load(self, url: str, model: ModelBase) -> models.Model:
        if self.is_local_url(url):
            # print(url)
            # assert False, "Stopped here"
            return self.load_local_object(url, model)

        data = self.fetch_object(url)
        return get_model_instance_with_gegevensgroeps(model, data, loader=self)


def get_model_instance_with_gegevensgroeps(
    model: ModelBase, data: Dict[str, Any], loader
) -> models.Model:
    field_names = [
        field.name for field in model._meta.get_fields() if not field.auto_created
    ] + ["url"]
    initial_data = data.copy()

    # modify data to include gegevensgroeps members
    gegevensgroeps = [
        (a, b) for a, b in getmembers(model) if isinstance(b, GegevensGroepType)
    ]
    for gegevensgroep__name, gegevensgroep in gegevensgroeps:
        if gegevensgroep__name in data:
            group_data = data.pop(gegevensgroep__name)

            for field, field_value in group_data.items():
                field_name = gegevensgroep.mapping[field].name
                data[field_name] = field_value

    # only keep known fields
    data = {key: value for key, value in data.items() if key in field_names}

    virtual_model = virtual_model_factory(model, loader=loader)
    return virtual_model(initial_data=initial_data, **data)
