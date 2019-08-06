from vng_api_common.validators import ResourceValidator as _ResourceValidator
from django.db import models


class ResourceValidator(_ResourceValidator):
    def __call__(self, obj):
        if isinstance(obj, models.Model):
            return

        return super().__call__(obj)
