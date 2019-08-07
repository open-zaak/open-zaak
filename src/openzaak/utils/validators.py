from vng_api_common.validators import ResourceValidator as _ResourceValidator
from vng_api_common.utils import get_resource_for_path
from django.db import models


class ResourceValidator(_ResourceValidator):
    def __call__(self, obj):
        resource = get_resource_for_path(obj)

        return super().__call__(obj)
