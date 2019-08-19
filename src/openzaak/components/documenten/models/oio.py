import uuid
from dataclasses import dataclass
from typing import Union

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.documenten.models import EnkelvoudigInformatieObject
from openzaak.components.zaken.models import ZaakInformatieObject
from rest_framework.request import Request
from rest_framework.reverse import reverse


@dataclass
class ObjectInformatieObject:
    """
    Wrap the relationship between an object and a document.

    The relationship already exists on a database level, which takes care
    of integrity. This object is merely and interface to a serializer.
    """
    informatieobject: EnkelvoudigInformatieObject
    _object: Union[BesluitInformatieObject, ZaakInformatieObject]
    object_type: str
    request: Request

    @property
    def uuid(self) -> uuid.UUID:
        return self._object.uuid

    @property
    def obj_url(self) -> str:
        obj = getattr(self._object, self.object_type)
        return reverse(
            f"{self.object_type}-detail",
            kwargs={"uuid": obj.uuid},
            request=self.request
        )
