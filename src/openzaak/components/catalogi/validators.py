# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from typing import List, Tuple, TypedDict

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
)

from openzaak.client import fetch_object
from openzaak.utils.dict import get_by_path

from .constants import SelectielijstKlasseProcestermijn as Procestermijn
from .models import ZaakType


class ArchiefProcedure(TypedDict):
    afleidingswijze: str
    datumkenmerk: str
    einddatum_bekend: bool
    objecttype: str
    registratie: str
    procestermijn: str


AFLEIDINGSWIJZE_VALIDATION_RULES = {
    Afleidingswijze.afgehandeld: {
        "procestermijn": False,
        "datumkenmerk": False,
        "einddatum_bekend": False,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.ander_datumkenmerk: {
        "procestermijn": False,
        "datumkenmerk": True,
        "objecttype": True,
        "registratie": True,
    },
    Afleidingswijze.eigenschap: {
        "procestermijn": False,
        "datumkenmerk": True,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.gerelateerde_zaak: {
        "procestermijn": False,
        "datumkenmerk": False,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.hoofdzaak: {
        "procestermijn": False,
        "datumkenmerk": False,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.ingangsdatum_besluit: {
        "procestermijn": False,
        "datumkenmerk": False,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.termijn: {
        "procestermijn": True,
        "datumkenmerk": False,
        "einddatum_bekend": False,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.vervaldatum_besluit: {
        "procestermijn": False,
        "datumkenmerk": False,
        "objecttype": False,
        "registratie": False,
    },
    Afleidingswijze.zaakobject: {
        "procestermijn": False,
        "datumkenmerk": True,
        "objecttype": True,
        "registratie": False,
    },
}


def validate_brondatumarchiefprocedure(
    data: ArchiefProcedure,
) -> Tuple[bool, List[str], List[str]]:
    mapping = AFLEIDINGSWIJZE_VALIDATION_RULES[data["afleidingswijze"]]
    error = False
    empty = []
    required = []
    for key, value in mapping.items():
        if bool(data.get(key)) != value:
            error = True
            if value:
                required.append(key)
            else:
                empty.append(key)
    return error, empty, required


def validate_zaaktype_for_publish(zaaktype: ZaakType) -> List[Tuple[str, str]]:
    """
    Validates that a ZaakType has the correct number of related object
    :param zaaktype: ZaakType object
    :return: list of tuples containing field name and error text
    """

    errors = []

    if (
        zaaktype.besluittypen.filter(concept=True).exists()
        or zaaktype.informatieobjecttypen.filter(concept=True).exists()
    ):
        errors.append((None, _("All related resources should be published")))

    has_invalid_resultaattypen = zaaktype.resultaattypen.filter(
        selectielijstklasse=""
    ).exists()
    if has_invalid_resultaattypen:
        errors.append(
            (
                "resultaattypen",
                _(
                    "This zaaktype has resultaattypen without a selectielijstklasse. "
                    "Please specify those before publishing the zaaktype."
                ),
            )
        )

    num_roltypen = zaaktype.roltype_set.count()
    if not num_roltypen >= 1:
        errors.append(
            (
                "roltypen",
                _("Publishing a zaaktype requires at least one roltype to be defined."),
            )
        )

    num_resultaattypen = zaaktype.resultaattypen.count()
    if not num_resultaattypen >= 1:
        errors.append(
            (
                "resultaattypen",
                _(
                    "Publishing a zaaktype requires at least one resultaattype to be defined."
                ),
            )
        )

    num_statustypen = zaaktype.statustypen.count()
    if not num_statustypen >= 2:
        errors.append(
            (
                "statustypen",
                _(
                    "Publishing a zaaktype requires at least two statustypes to be defined."
                ),
            )
        )

    return errors


class ProcestermijnAfleidingswijzeValidator:
    code = "invalid-afleidingswijze-for-procestermijn"
    message = _(
        "afleidingswijze must be {} when selectielijstklasse.procestermijn is {}"
    )
    message_invalid_procestermijn = _(
        "afleidingswijze cannot be {} when selectielijstklasse.procestermijn is {}"
    )

    def __init__(
        self,
        selectielijstklasse_field: str,
        afleidingswijze_field_path: str = "brondatum_archiefprocedure.afleidingswijze",
    ):
        self.selectielijstklasse_field = selectielijstklasse_field
        self.afleidingswijze_field_path = afleidingswijze_field_path

    def __call__(self, attrs: dict) -> None:
        selectielijstklasse_url = attrs.get(self.selectielijstklasse_field)
        afleidingswijze = get_by_path(attrs, self.afleidingswijze_field_path)

        if not selectielijstklasse_url or not afleidingswijze:
            return

        selectielijstklasse = fetch_object(selectielijstklasse_url)
        procestermijn = selectielijstklasse["procestermijn"]

        if not procestermijn:
            return

        if (  # noqa
            procestermijn == Procestermijn.nihil
            and afleidingswijze != Afleidingswijze.afgehandeld
        ):
            raise ValidationError(
                self.message.format(Afleidingswijze.afgehandeld, procestermijn),
                code=self.code,
            )
        elif (
            procestermijn == Procestermijn.ingeschatte_bestaansduur_procesobject
            and afleidingswijze != Afleidingswijze.termijn
        ):
            raise ValidationError(
                self.message.format(Afleidingswijze.termijn, procestermijn),
                code=self.code,
            )
        elif (
            procestermijn != Procestermijn.nihil
            and afleidingswijze == Afleidingswijze.afgehandeld
        ):
            raise ValidationError(
                self.message_invalid_procestermijn.format(
                    afleidingswijze, procestermijn
                ),
                code=self.code,
            )
