import uuid as _uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from vng_api_common.fields import VertrouwelijkheidsAanduidingField

from .mixins import ConceptMixin, GeldigheidMixin


class InformatieObjectTypeOmschrijvingGeneriek(GeldigheidMixin, models.Model):
    """
    Algemeen binnen de overheid gehanteerde omschrijvingen van de typen informatieobjecten

    **Toelichting referentielijst**
    Deze 'lijst' bevat de benamingen van de generieke informatieobjecttypen die in de informatie-uitwisseling betrokken
    zijn.

    Het gaat telkens om een korte omschrijving van de aard van een informatieobject, ook wel 'documentnaam' genoemd,
    zoals deze landelijk binnen de overheid wordt toegepast op basis van de ZTC. De 'lijst' betreft dus geen
    informatieobjecttypen voor specifieke domeinen en ook geen organisatiespecifieke informatieobjecttypen.

    """

    informatieobjecttype_omschrijving_generiek = models.CharField(
        _("informatieobjecttype omschrijving generiek"),
        max_length=80,
        help_text=_("Algemeen gehanteerde omschrijving van het type informatieobject."),
    )
    definitie_informatieobjecttype_omschrijving_generiek = models.CharField(
        _("definitie"),
        max_length=255,
        help_text=_("Nauwkeurige beschrijving van het generieke type informatieobject"),
    )
    herkomst_informatieobjecttype_omschrijving_generiek = models.CharField(
        _("herkomst"),
        max_length=12,
        help_text=_(
            "De naam van de waardenverzameling, of van de beherende "
            "organisatie daarvan, waaruit de waarde is overgenomen."
        ),
    )
    hierarchie_informatieobjecttype_omschrijving_generiek = models.CharField(
        _("hierarchie"),
        max_length=80,
        help_text=_("De plaats in de rangorde van het informatieobjecttype."),
    )
    opmerking_informatieobjecttype_omschrijving_generiek = models.CharField(
        _("opmerking"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Zinvolle toelichting bij het informatieobjecttype"),
    )

    class Meta:
        verbose_name = _("Generieke informatieobjecttype-omschrijving")
        verbose_name_plural = _("Generieke informatieobjecttype-omschrijvingen")

    def __str__(self):
        return self.informatieobjecttype_omschrijving_generiek

    def clean(self):
        """
        Er is alleen een regel voor datum_einde_geldigheid:
        Alleen een datum die gelijk is aan of die gelegen is na de datum zoals opgenomen onder 'Datum
        begin geldigheid’ kan in de registratie worden opgenomen.
        """
        super().clean()


class InformatieObjectType(GeldigheidMixin, ConceptMixin, models.Model):
    """
    Aanduiding van de aard van INFORMATIEOBJECTen zoals gehanteerd door de zaakbehandelende organisatie.

    Unieke aanduiding van CATALOGUS in combinatie met Informatieobjecttype-omschrijving.
    """

    uuid = models.UUIDField(
        unique=True, default=_uuid.uuid4, help_text="Unieke resource identifier (UUID4)"
    )
    omschrijving = models.CharField(
        _("omschrijving"),
        max_length=80,
        help_text=_(
            "Omschrijving van de aard van informatieobjecten van dit INFORMATIEOBJECTTYPE."
        ),
    )
    omschrijving_generiek = models.ForeignKey(
        "catalogi.InformatieObjectTypeOmschrijvingGeneriek",
        verbose_name=_("omschrijving generiek"),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text=_("Algemeen gehanteerde omschrijving van het INFORMATIEOBJECTTYPE."),
    )
    informatieobjectcategorie = models.CharField(
        _("categorie"),
        max_length=80,
        help_text=_(
            "Typering van de aard van informatieobjecten van dit INFORMATIEOBJECTTYPE."
        ),
    )
    trefwoord = ArrayField(
        models.CharField(_("trefwoord"), max_length=30),
        default=list,
        blank=True,
        help_text=_(
            "Trefwoord(en) waarmee informatieobjecten van het INFORMATIEOBJECTTYPE kunnen worden "
            "gekarakteriseerd. (Gebruik een komma om waarden van elkaar te onderscheiden.)"
        ),
    )
    vertrouwelijkheidaanduiding = VertrouwelijkheidsAanduidingField(
        _("vertrouwelijkheidaanduiding"),
        help_text=_(
            "Aanduiding van de mate waarin informatieobjecten van dit INFORMATIEOBJECTTYPE voor de "
            "openbaarheid bestemd zijn."
        ),
    )
    model = ArrayField(
        models.URLField(_("model")),
        blank=True,
        default=list,
        help_text=_(
            "De URL naar het model / sjabloon dat wordt gebruikt voor de creatie van informatieobjecten "
            "van dit INFORMATIEOBJECTTYPE. (Gebruik een komma om waarden van elkaar te onderscheiden.)"
        ),
    )
    toelichting = models.CharField(
        _("toelichting"),
        max_length=1000,
        blank=True,
        null=True,
        help_text=_("Een eventuele toelichting op dit INFORMATIEOBJECTTYPE."),
    )

    catalogus = models.ForeignKey(
        "catalogi.Catalogus",
        verbose_name=_("maakt deel uit van"),
        on_delete=models.CASCADE,
        help_text=(
            "URL-referentie naar de CATALOGUS waartoe dit INFORMATIEOBJECTTYPE behoort."
        ),
    )

    zaaktypes = models.ManyToManyField(
        "catalogi.ZaakType",
        verbose_name=_("zaaktypes"),
        related_name="heeft_relevant_informatieobjecttype",
        through="catalogi.ZaakInformatieobjectType",
        help_text=_(
            "ZAAKTYPE met ZAAKen die relevant kunnen zijn voor dit INFORMATIEOBJECTTYPE"
        ),
    )

    class Meta:
        unique_together = ("catalogus", "omschrijving")
        verbose_name = _("Informatieobjecttype")
        verbose_name_plural = _("Informatieobjecttypen")

    def __str__(self):
        return "{} - {}".format(self.catalogus, self.omschrijving)
