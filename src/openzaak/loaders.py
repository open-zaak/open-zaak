# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import json
from contextvars import ContextVar
from inspect import getmembers
from typing import Any, Dict

from django.db import models
from django.db.models.base import ModelBase

import requests
from django_loose_fk.loaders import BaseLoader, FetchError, FetchJsonError
from django_loose_fk.virtual_models import virtual_model_factory
from djangorestframework_camel_case.util import underscoreize
from vng_api_common.client import get_client
from vng_api_common.descriptors import GegevensGroepType

_clients: dict = {}
_fetch_cache: ContextVar[dict] = ContextVar("loose_fk_fetch_cache")


def _get_cache() -> dict:
    try:
        return _fetch_cache.get()
    except LookupError:
        cache: dict = {}
        _fetch_cache.set(cache)
        return cache


def clear_fetch_cache() -> None:
    _fetch_cache.set({})


class AuthorizedRequestsLoader(BaseLoader):
    """
    Fetch external API objects with Authorization header.
    """

    @staticmethod
    def fetch_object(url: str, do_underscoreize=True) -> dict:
        cache = _get_cache()

        if url in cache:
            data = cache[url]
        else:
            client = get_client(url, raise_exceptions=True)
            if client is None:
                raise FetchError(f"No service configured for url {url}")

            api_root = client.base_url
            client = _clients.setdefault(api_root, client)

            try:
                response = client.get(url, headers={"Accept-Crs": "EPSG:4326"})
            except requests.exceptions.RequestException as exc:
                raise FetchError(exc.args[0]) from exc

            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                raise FetchError(exc.args[0]) from exc

            try:
                data = response.json()
            except json.JSONDecodeError as exc:
                raise FetchJsonError(exc.args[0]) from exc

            cache[url] = data

        if not do_underscoreize:
            return dict(data) if isinstance(data, dict) else data

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

            if group_data is None:
                continue

            for field, field_value in group_data.items():
                field_name = gegevensgroep.mapping[field].name
                data[field_name] = field_value

    # only keep known fields
    data = {key: value for key, value in data.items() if key in field_names}

    virtual_model = virtual_model_factory(model, loader=loader)
    return virtual_model(initial_data=initial_data, **data)
