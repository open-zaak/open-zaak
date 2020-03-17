from django.db import models
from django.utils.translation import ugettext_lazy as _

from solo.models import SingletonModel

from .constants import NLXDirectories


class NLXConfig(SingletonModel):
    directory = models.CharField(
        _("NLX directory"), max_length=50, choices=NLXDirectories.choices, blank=True
    )
    outway = models.URLField(_("outway address"), blank=True)

    class Meta:
        verbose_name = _("NLX configuration")
