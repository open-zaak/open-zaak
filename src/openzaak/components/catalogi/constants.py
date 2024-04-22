# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.db import models
from django.utils.translation import gettext_lazy as _


class SelectielijstKlasseProcestermijn(models.TextChoices):
    nihil = (
        "nihil",
        _(
            "Er is geen aparte procestermijn, de bewaartermijn start direct na de procesfase."
        ),
    )
    ingeschatte_bestaansduur_procesobject = (
        "ingeschatte_bestaansduur_procesobject",
        _(
            "Er wordt een inschatting gemaakt van de maximale bestaans-of geldigheidsduur van het procesobject, "
            "ongeacht de daadwerkelijke duur. Dit kan bijvoorbeeld al vastgelegd worden in het zaaktype, zodat "
            "procestermijn en bewaartermijn samen een bewaartermijn vormen die direct kan gaan lopen na de procesfase."
        ),
    )


class FormaatChoices(models.TextChoices):
    tekst = "tekst", _("Tekst")
    getal = "getal", _("Getal")
    datum = "datum", _("Datum")
    datum_tijd = "datum_tijd", _("Datum/tijd")


class ArchiefProcedure(models.TextChoices):
    afgehandeld = "afgehandeld", _("Afgehandeld")
    ingangsdatum_besluit = "ingangsdatum_besluit", _("Ingangsdatum besluit")
    vervaldatum_besluit = "vervaldatum_besluit", _("Vervaldatum besluit")
    eigenschap = "eigenschap", _("Eigenschap")
    ander_datumkenmerk = "ander_datumkenmerk", _("Ander datumkenmerk")


class InternExtern(models.TextChoices):
    intern = "intern", _("Intern")
    extern = "extern", _("Extern")


class RichtingChoices(models.TextChoices):
    inkomend = "inkomend", _("Inkomend")
    intern = "intern", _("Intern")
    uitgaand = "uitgaand", _("Uitgaand")


class ArchiefNominatieChoices(models.TextChoices):
    blijvend_bewaren = "blijvend_bewaren", _("Blijvend bewaren")
    vernietigen = "vernietigen", _("Vernietigen")


class AardRelatieChoices(models.TextChoices):
    # een zaak van het ZAAKTYPE is een te plannen vervolg op een
    # zaak van het andere ZAAKTYPE
    vervolg = "vervolg", _("Vervolg")

    # een zaak van het ZAAKTYPE levert een bijdrage aan het bereiken van de
    # uitkomst van een zaak van het andere ZAAKTYPE
    bijdrage = "bijdrage", _("Bijdrage")

    # een zaak van het ZAAKTYPE heeft betrekking op een zaak van het
    # andere ZAAKTYPE of een zaak van het andere ZAAKTYPE is relevant voor
    # of is onderwerp van een zaak van het ZAAKTYPE
    onderwerp = "onderwerp", _("Onderwerp")


IMPORT_ORDER = [
    "Catalogus",
    "InformatieObjectType",
    "BesluitType",
    "ZaakType",
    "StatusType",
    "ZaakTypeInformatieObjectType",
    "ResultaatType",
    "RolType",
    "Eigenschap",
]
