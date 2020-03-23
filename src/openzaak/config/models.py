from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from solo.models import SingletonModel

from .constants import NLXDirectories


class NLXConfig(SingletonModel):
    directory = models.CharField(
        _("NLX directory"), max_length=50, choices=NLXDirectories.choices, blank=True
    )
    outway = models.URLField(_("outway address"), blank=True, help_text=_("Example: http://my-outway.nlx:8080")

    class Meta:
        verbose_name = _("NLX configuration")

    @property
    def directory_url(self) -> str:
        return settings.NLX_DIRECTORY_URLS.get(self.directory, "")
