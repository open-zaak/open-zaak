from typing import Union

from openzaak.components.besluiten.models import BesluitInformatieObject
from openzaak.components.zaken.models import ZaakInformatieObject

IORelation = Union[BesluitInformatieObject, ZaakInformatieObject]
