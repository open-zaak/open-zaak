from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from solo.models import SingletonModel
from vng_api_common.constants import ComponentTypes

from openzaak.utils.constants import COMPONENT_MAPPING

from .constants import NLXDirectories


class NLXConfig(SingletonModel):
    directory = models.CharField(
        _("NLX directory"), max_length=50, choices=NLXDirectories.choices, blank=True
    )
    outway = models.URLField(
        _("outway address"),
        blank=True,
        help_text=_("Example: http://my-outway.nlx:8080"),
    )

    class Meta:
        verbose_name = _("NLX configuration")

    @property
    def directory_url(self) -> str:
        return settings.NLX_DIRECTORY_URLS.get(self.directory, "")


class InternalService(models.Model):
    api_type = models.CharField(
        _("API type"), max_length=50, choices=ComponentTypes.choices, unique=True
    )
    enabled = models.BooleanField(
        _("enabled"),
        default=True,
        help_text=_("Boolean indicates if internal API is enabled"),
    )
    nlx = models.BooleanField(
        _("nlx"),
        default=True,
        help_text=_("Boolean indicated if the service is available via NLX inway"),
    )

    class Meta:
        verbose_name = _("Internal service")
        verbose_name_plural = _("Internal services")

    def __str__(self):
        return self.api_type

    @property
    def component(self) -> str:
        return COMPONENT_MAPPING.get(self.api_type, "")
