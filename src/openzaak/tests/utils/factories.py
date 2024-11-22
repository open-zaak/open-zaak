# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from furl import furl
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.utils.fields import FkOrServiceUrlField


class FkOrServiceUrlFactoryMixin:
    """
    create service instances for composite url fields
    """

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        post_generation hook can't be used since services should exist during factory.create()
        """

        services = []
        fields = [
            f.name
            for f in model_class._meta.get_fields()
            if isinstance(f, FkOrServiceUrlField)
        ]
        for field in fields:
            value = kwargs.get(field)
            if not value:
                continue

            if not isinstance(value, str):
                continue

            # create Service instance for composite field
            base_url = furl(value).origin
            services.append(
                Service(api_root=base_url, slug=base_url, api_type=APITypes.orc)
            )

        Service.objects.bulk_create(services, ignore_conflicts=True)

        return super()._create(model_class, *args, **kwargs)
