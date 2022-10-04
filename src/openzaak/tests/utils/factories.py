from furl import furl
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from openzaak.utils.fields import FkOrServiceUrlField


class FkOrServiceUrlFactoryMixin:
    """
    create service instances for composite url fields
    create service for provided parameter 'local_host'
    """

    local_host = "http://testserver/"  # use to create service for local api

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
            services.append(Service(api_root=base_url, api_type=APITypes.orc))
            # service, created = Service.objects.get_or_create(api_root=base_url, defaults={"api_type": APITypes.orc})

        # if local host specified create service for it
        local_host = kwargs.pop("local_host", cls.local_host)
        if local_host:
            services.append(Service(api_root=local_host, api_type=APITypes.orc))

        Service.objects.bulk_create(services, ignore_conflicts=True)

        return super()._create(model_class, *args, **kwargs)
