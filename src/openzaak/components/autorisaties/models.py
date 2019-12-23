from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from vng_api_common.authorizations.models import Applicatie
from vng_api_common.constants import ComponentTypes
from vng_api_common.fields import VertrouwelijkheidsAanduidingField


class AutorisatieSpec(models.Model):
    """
    Specification for Autorisatie to install.

    If a spec exists, it will be applied when a ZaakType, InformatieObjectType
    or BesluitType is created.
    """

    applicatie = models.ForeignKey(
        Applicatie,
        on_delete=models.CASCADE,
        related_name="autorisatie_specs",
        verbose_name=_("applicatie"),
    )
    component = models.CharField(
        _("component"),
        max_length=50,
        choices=ComponentTypes.choices,
        help_text=_("Component waarop autorisatie van toepassing is."),
    )
    scopes = ArrayField(
        models.CharField(max_length=100),
        verbose_name=_("scopes"),
        help_text=_("Komma-gescheiden lijst van scope labels."),
    )
    max_vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduidingField(
        help_text=_("Maximaal toegelaten vertrouwelijkheidaanduiding (inclusief)."),
        blank=True,
    )

    class Meta:
        verbose_name = _("autorisatiespec")
        verbose_name_plural = _("autorisatiespecs")
        # since the spec implicates this config is valid for _all_ zaaktypen/
        # informatieobjecttypen/besluittypen, the scopes/VA are constant for
        # these. The exact *type is implied by the component choice, so we need
        # a unique constraint on applicatie + component
        unique_together = ("applicatie", "component")

    def __str__(self):
        return _("{component} autorisatiespec voor {app}").format(
            component=self.get_component_display(), app=self.applicatie
        )
