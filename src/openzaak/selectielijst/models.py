from django.utils.translation import ugettext_lazy as _

from vng_api_common.decorators import field_default
from vng_api_common.models import ClientConfig


@field_default("api_root", "https://referentielijsten-api.vng.cloud/api/v1/")
class ReferentieLijstConfig(ClientConfig):
    class Meta:
        verbose_name = _("ReferentieLijstconfiguratie")
