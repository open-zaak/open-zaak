# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import copy
import json
import time
from inspect import getmembers
from typing import Any, Dict

from django.db import models
from django.db.models.base import ModelBase

import requests
from django_loose_fk.loaders import BaseLoader, FetchError, FetchJsonError
from django_loose_fk.virtual_models import virtual_model_factory
from djangorestframework_camel_case.util import underscoreize
from vng_api_common.client import NoServiceConfigured, get_client
from vng_api_common.descriptors import GegevensGroepType


class AuthorizedRequestsLoader(BaseLoader):
    """
    Fetch external API objects through the client of their configured Service.

    Fetched data is cached per URL together with its ETag, at class level:
    - within ``revalidate_after`` seconds it is reused without a request;
    - after that it's revalidated with ``If-None-Match``;
    - an HTTP error drops the cached entry.
    """

    revalidate_after = 5  # seconds
    max_cached = 1000

    # url -> (validated_at, etag, data)
    _cache: dict[str, tuple[float, str, dict]] = {}

    @classmethod
    def fetch_object(cls, url: str, do_underscoreize=True) -> dict:
        now = time.monotonic()
        cached = cls._cache.get(url)

        if cached is not None and now - cached[0] < cls.revalidate_after:
            data = copy.deepcopy(cached[2])

        else:
            headers = {}
            if cached is not None:
                headers["If-None-Match"] = cached[1]

            try:
                with get_client(url, raise_exceptions=True) as client:
                    response = client.get(url, headers=headers)
            except NoServiceConfigured as exc:
                raise FetchError(exc.args[0]) from exc
            except requests.exceptions.RequestException as exc:
                raise FetchError(exc.args[0]) from exc

            if response.status_code == 304 and cached is not None:
                cls._cache[url] = (now, cached[1], cached[2])
                data = copy.deepcopy(cached[2])
            else:
                try:
                    response.raise_for_status()
                except requests.HTTPError as exc:
                    cls._cache.pop(url, None)
                    raise FetchError(exc.args[0]) from exc

                try:
                    data = response.json()
                except json.JSONDecodeError as exc:
                    cls._cache.pop(url, None)
                    raise FetchJsonError(exc.args[0]) from exc

                etag = response.headers.get("ETag")
                if etag:
                    cls._cache[url] = (now, etag, copy.deepcopy(data))
                    while len(cls._cache) > cls.max_cached:
                        try:
                            evicted = next(iter(cls._cache))
                            cls._cache.pop(evicted, None)
                        except (StopIteration, RuntimeError):
                            break
                else:
                    cls._cache.pop(url, None)

        if not do_underscoreize:
            return data
        return underscoreize(data)

    def load(self, url: str, model: ModelBase) -> models.Model:
        if self.is_local_url(url):
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
