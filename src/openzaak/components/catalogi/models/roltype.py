# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from vng_api_common.constants import RolOmschrijving


class RolType(models.Model):
    """
    Generieke aanduiding van de aard van een ROL die een BETROKKENE kan
    uitoefenen in ZAAKen van een ZAAKTYPE.

    Toelichting objecttype
    Zowel in de GEMMA-procesarchitectuur, het RGBZ als de ZTC komt het begrip ‘rol’ voor. De
    interpretatie daarvan hebben we geharmoniseerd.
    Onder ‘rol’ verstaan we de aard van de bijdrage die een extern persoon, medewerker, afdeling,
    bedrijf e.d. levert aan de behandeling van een zaak cq. de uitvoering van een bedrijfsproces.
    Het gaat hierbij om ‘wat’ iemand doet, niet om ‘wie’ het doet. Het gaat dus niet om functies
    van medewerkers binnen een organisatie maar om de taken die iemand uitvoert. Een rol kan in
    praktijksituaties dan ook toegewezen worden aan diverse functionarissen, afdelingen en
    externen. Ook kan het voor komen dat één medewerker meerdere rollen vervult of dat
    meerdere medewerkers samen één rol vervullen.
    Rolbenamingen zijn veelal specifiek voor het zaak- of procestype: subsidieaanvrager,
    inspecteur, juridisch adviseur, vergunningbehandelaar, bezwaarindiener, klager, etcetera. Om
    bij uitwisseling van zaak- en procesgegevens (binnen en tussen organisaties) te bereiken dat
    rolbenamingen juist geïnterpreteerd worden, hanteren we generieke rolbenamingen. Per
    zaaktype en proces kunnen deze verbijzonderd of zelfs uitgesplitst worden naar context-
    specifieke benamingen. Waar gesproken wordt van ‘zaak’ bedoelen we zowel ‘hoofdzaak’ als
    ‘deelzaak’.
    """

    uuid = models.UUIDField(default=uuid.uuid4)
    omschrijving = models.CharField(
        _("omschrijving"),
        max_length=100,
        help_text=_("Omschrijving van de aard van de ROL."),
    )
    omschrijving_generiek = models.CharField(
        _("omschrijving generiek"),
        max_length=20,
        choices=RolOmschrijving.choices,
        help_text=_("Algemeen gehanteerde omschrijving van de aard van de ROL."),
        db_index=True,
    )
    zaaktype = models.ForeignKey(
        "catalogi.ZaakType",
        # verbose_name=_("is van"),
        on_delete=models.CASCADE,
        help_text=_(
            "URL-referentie naar het ZAAKTYPE waar deze ROLTYPEn betrokken kunnen zijn."
        ),
    )

    class Meta:
        unique_together = ("zaaktype", "omschrijving")
        verbose_name = _("Roltype")
        verbose_name_plural = _("Roltypen")

    def __str__(self):
        return self.omschrijving
