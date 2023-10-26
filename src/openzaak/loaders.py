# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import json
from inspect import getmembers
from typing import Any, Dict

from django.db import models
from django.db.models.base import ModelBase

import requests
from django_loose_fk.loaders import BaseLoader, FetchError, FetchJsonError
from django_loose_fk.virtual_models import virtual_model_factory
from djangorestframework_camel_case.util import underscoreize
from vng_api_common.descriptors import GegevensGroepType


class AuthorizedRequestsLoader(BaseLoader):
    """
    Fetch external API objects with Authorization header.
    """

    @staticmethod
    def fetch_object(url: str, do_underscoreize=True) -> dict:
        from zgw_consumers.models import Service

        # TODO should we replace it with Service.get_client() and use it instead of requests?
        # but in this case we couldn't catch separate FetchJsonError
        client_auth_header = Service.get_auth_header(url)
        headers = client_auth_header or {}

        try:
            response = requests.get(url, headers=headers)
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
