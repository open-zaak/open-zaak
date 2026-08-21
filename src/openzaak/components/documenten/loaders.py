# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from urllib.parse import urlparse

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.base import ModelBase

from django_loose_fk.virtual_models import ProxyMixin
from vng_api_common.utils import get_resource_for_path

from openzaak.components.catalogi.models import InformatieObjectType
from openzaak.loaders import (
    AuthorizedRequestsLoader,
    get_model_instance_with_gegevensgroeps,
)


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

        if self.is_local_url(url):
            return self.load_local_object(url, model)

        data = self.fetch_object(url)
        model_instance = get_model_instance_with_gegevensgroeps(
            model, data, loader=self
        )
        self.add_missing_props(model, model_instance, data)
        return model_instance

    def resolve_io_type(self, url: str):
        try:
            return get_resource_for_path(urlparse(url).path)
        except ObjectDoesNotExist:
            return super().load(url, model=InformatieObjectType)

    def add_missing_props(
        self, model: ModelBase, model_instance: ProxyMixin, data: dict
    ) -> None:
        """
        Translate JSON response properties to Python props that are not model fields.
        """
        from openzaak.components.documenten.models import EnkelvoudigInformatieObject

        if not issubclass(model, EnkelvoudigInformatieObject):
            return

        model_instance.locked = data["locked"]
