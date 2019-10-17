from urllib.parse import urlparse

from django.db.models.base import ModelBase

from vng_api_common.utils import get_resource_for_path

from openzaak.components.catalogi.models import InformatieObjectType
from openzaak.loaders import AuthorizedRequestsLoader


class EIOLoader(AuthorizedRequestsLoader):
    """
    Load the EIO directly instead of going through EIOCanonical.
    """

    def load(self, url: str, model: ModelBase):
        from openzaak.components.documenten.models import (
            EnkelvoudigInformatieObject,
            EnkelvoudigInformatieObjectCanonical,
        )

        if model is EnkelvoudigInformatieObjectCanonical:
            model = EnkelvoudigInformatieObject

        if model is InformatieObjectType:
            return self.resolve_io_type(url)

        return super().load(url, model=model)

    def resolve_io_type(self, url: str):
        try:
            return get_resource_for_path(urlparse(url).path)
        except InformatieObjectType.DoesNotExist:
            return super().load(url, model=InformatieObjectType)
