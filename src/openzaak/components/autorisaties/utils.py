# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Any, Dict, Optional, Union

from django.contrib.sites.models import Site
from django.db.models.base import ModelBase
from django.http import HttpRequest

import dictdiffer
from rest_framework.request import Request
from rest_framework.settings import api_settings
from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.authorizations.serializers import ApplicatieSerializer
from vng_api_common.constants import ComponentTypes

from openzaak.components.catalogi.models import (
    BesluitType,
    InformatieObjectType,
    ZaakType,
)

from .api.viewsets import ApplicatieViewSet

RelatedTypeObject = Union[ZaakType, InformatieObjectType, BesluitType]


def _get_related_object(model: ModelBase, url: str) -> Optional[RelatedTypeObject]:
    if url == "":
        return None
    uuid = url.rsplit("/")[-1]
    obj = model.objects.get(uuid=uuid)
    return obj


def get_related_object(autorisatie: Autorisatie) -> Optional[RelatedTypeObject]:
    if autorisatie.component == ComponentTypes.zrc:
        return _get_related_object(ZaakType, autorisatie.zaaktype)

    if autorisatie.component == ComponentTypes.drc:
        return _get_related_object(
            InformatieObjectType, autorisatie.informatieobjecttype
        )

    if autorisatie.component == ComponentTypes.brc:
        return _get_related_object(BesluitType, autorisatie.besluittype)

    return None


def sort_key(item: Any):
    if not isinstance(item, dict):
        return item

    return tuple(item.items())


def _normalize_list_order(obj: Any) -> Any:
    if isinstance(obj, list):
        return sorted([_normalize_list_order(item) for item in obj], key=sort_key)
    elif isinstance(obj, dict):
        return {key: _normalize_list_order(value) for key, value in obj.items()}
    else:
        return obj


def get_applicatie_serializer(
    applicatie: Applicatie, request: HttpRequest
) -> ApplicatieSerializer:
    """
    Wrap the request into a DRF-suitable request.
    """
    request = Request(request)
    scheme = api_settings.DEFAULT_VERSIONING_CLASS()
    request.version, request.versioning_scheme = (
        scheme.determine_version(request, version=api_settings.DEFAULT_VERSION),
        scheme,
    )
    serializer = ApplicatieSerializer(instance=applicatie, context={"request": request})
    return serializer


def versions_equivalent(version1: Dict[str, Any], version2: Dict[str, Any]) -> bool:
    """
    Compare if two dicts are different or not.

    Comparisons assumes that ordering in lists does not matter!
    """
    # pre-process to change lists into sets
    version1 = _normalize_list_order(version1)
    version2 = _normalize_list_order(version2)
    return not any(dictdiffer.diff(version1, version2))


def send_applicatie_changed_notification(
    applicatie: Applicatie, new_version: Optional[Dict[str, Any]] = None
):
    viewset = ApplicatieViewSet()
    viewset.action = "update"
    if new_version is None:
        request = HttpRequest()
        request.META["HTTP_HOST"] = Site.objects.get_current().domain
        new_version = get_applicatie_serializer(applicatie, request).data
    viewset.notify(status_code=200, data=new_version, instance=applicatie)
