# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class SelectielijstKlasseProcestermijn(DjangoChoices):
    nihil = ChoiceItem(
        "nihil",
        _(
            "Er is geen aparte procestermijn, de bewaartermijn start direct na de procesfase."
        ),
    )
    ingeschatte_bestaansduur_procesobject = ChoiceItem(
        "ingeschatte_bestaansduur_procesobject",
        _(
            "Er wordt een inschatting gemaakt van de maximale bestaans-of geldigheidsduur van het procesobject, "
            "ongeacht de daadwerkelijke duur. Dit kan bijvoorbeeld al vastgelegd worden in het zaaktype, zodat "
            "procestermijn en bewaartermijn samen een bewaartermijn vormen die direct kan gaan lopen na de procesfase."
        ),
    )


class FormaatChoices(DjangoChoices):
    tekst = ChoiceItem("tekst", _("Tekst"))
    getal = ChoiceItem("getal", _("Getal"))
    datum = ChoiceItem("datum", _("Datum"))
    datum_tijd = ChoiceItem("datum_tijd", _("Datum/tijd"))


class ArchiefProcedure(DjangoChoices):
    afgehandeld = ChoiceItem("afgehandeld", _("Afgehandeld"))
    ingangsdatum_besluit = ChoiceItem("ingangsdatum_besluit", _("Ingangsdatum besluit"))
    vervaldatum_besluit = ChoiceItem("vervaldatum_besluit", _("Vervaldatum besluit"))
    eigenschap = ChoiceItem("eigenschap", _("Eigenschap"))
    ander_datumkenmerk = ChoiceItem("ander_datumkenmerk", _("Ander datumkenmerk"))


class InternExtern(DjangoChoices):
    intern = ChoiceItem("intern", _("Intern"))
    extern = ChoiceItem("extern", _("Extern"))


class RichtingChoices(DjangoChoices):
    inkomend = ChoiceItem("inkomend", _("Inkomend"))
    intern = ChoiceItem("intern", _("Intern"))
    uitgaand = ChoiceItem("uitgaand", _("Uitgaand"))


class ArchiefNominatieChoices(DjangoChoices):
    blijvend_bewaren = ChoiceItem("blijvend_bewaren", _("Blijvend bewaren"))
    vernietigen = ChoiceItem("vernietigen", _("Vernietigen"))


class AardRelatieChoices(DjangoChoices):
    # een zaak van het ZAAKTYPE is een te plannen vervolg op een
    # zaak van het andere ZAAKTYPE
    vervolg = ChoiceItem("vervolg", _("Vervolg"))

    # een zaak van het ZAAKTYPE levert een bijdrage aan het bereiken van de
    # uitkomst van een zaak van het andere ZAAKTYPE
    bijdrage = ChoiceItem("bijdrage", _("Bijdrage"))

    # een zaak van het ZAAKTYPE heeft betrekking op een zaak van het
    # andere ZAAKTYPE of een zaak van het andere ZAAKTYPE is relevant voor
    # of is onderwerp van een zaak van het ZAAKTYPE
    onderwerp = ChoiceItem("onderwerp", _("Onderwerp"))


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
