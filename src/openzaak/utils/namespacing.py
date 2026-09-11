# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Dimpact
from typing import NotRequired, TypedDict

from django.db import models

from rest_framework.request import Request


class ReplaceUrlConfig(TypedDict):
    field: str
    namespace: NotRequired[str]  # kanaal.label override


def replace_namespace(url: str, namespace: str) -> str:
    prefix, sep, rest = url.partition("/api")
    if not sep:
        return url

    base, _, old_namespace = prefix.rpartition("/")
    return f"{base}/{namespace}{sep}{rest}"


def replace_namespaces(data: dict, fields: list[str], namespace: str) -> dict:
    new_data = data.copy()
    for field in fields:
        new_data[field] = replace_namespace(new_data[field], namespace)

    return new_data


def replace_namespaces_from_config(
    data, configs: list[ReplaceUrlConfig], namespace: str
) -> ReplaceUrlConfig:
    new_data = data.copy()
    for config in configs:
        new_data[config["field"]] = replace_namespace(
            new_data[config["field"]], config.get("namespace", namespace)
        )

    return new_data


def get_nested_main_object_url_from_instance(
    key: str, instance: models.Model, request: Request
) -> str | None:
    """Returns the url of a nested FK field"""
    obj = instance
    for field in key.split("."):
        obj = getattr(obj, field, None)
    return obj.get_absolute_api_url(request=request) if obj else None


def get_nested_main_object_url_from_dict(key: str, data: object) -> str | None:
    """Returns a nested url field from a dict"""
    for field in key.split("."):
        if not isinstance(data, dict):
            raise KeyError
        data = data.get(field)
    return data if isinstance(data, str) else None
