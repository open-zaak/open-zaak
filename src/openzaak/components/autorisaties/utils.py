from typing import Optional, Union

from django.db.models.base import ModelBase

from vng_api_common.authorizations.models import Applicatie, Autorisatie
from vng_api_common.constants import ComponentTypes

from openzaak.components.catalogi.models import (
    BesluitType,
    InformatieObjectType,
    ZaakType,
)

RelatedTypeObject = Union[ZaakType, InformatieObjectType, BesluitType]


def _get_related_object(model: ModelBase, url: str) -> RelatedTypeObject:
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


def send_applicatie_changed_notification(applicatie: Applicatie):
    raise NotImplementedError
