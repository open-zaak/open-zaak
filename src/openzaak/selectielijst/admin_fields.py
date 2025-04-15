# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
"""
Integrations of selectielijst API into Django admin.
"""
from typing import Optional

from django import forms
from django.contrib.admin import widgets
from django.db.models import Field
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from ape_pie.exceptions import InvalidURLError

from .api import (
    get_procestypen,
    get_resultaattype_omschrijvingen,
    get_resultaten,
    retrieve_procestype,
    retrieve_resultaat,
    retrieve_resultaattype_omschrijvingen,
)


def get_procestype_field(
    db_field: Field, request: HttpRequest, procestype_jaar: int, **kwargs
) -> forms.ChoiceField:
    choices = (
        (
            procestype["url"],
            f"{procestype['nummer']} - {procestype['naam']}",
        )
        for procestype in get_procestypen(procestype_jaar=procestype_jaar)
    )

    return forms.ChoiceField(
        label=db_field.verbose_name.capitalize(),
        choices=choices,
        required=False,
        help_text=db_field.help_text,
    )


def get_selectielijst_resultaat_choices(proces_type: Optional[str] = None):
    choices = []
    for resultaat in get_resultaten(proces_type):
        description = f"{resultaat['volledigNummer']} - {resultaat['naam']} - {resultaat['waardering']}"
        if resultaat["bewaartermijn"]:
            description = description + f" - {resultaat['bewaartermijn']}"
        if resultaat["omschrijving"]:
            description = description + f" - {resultaat['omschrijving']}"
        choices.append((resultaat["url"], description))
    return choices


def get_selectielijstklasse_field(
    db_field: Field, request: HttpRequest, **kwargs
) -> forms.ChoiceField:
    return forms.ChoiceField(
        label=db_field.verbose_name.capitalize(),
        choices=get_selectielijst_resultaat_choices(kwargs.get("procestype")),
        required=not db_field.blank,
        help_text=db_field.help_text,
        widget=widgets.AdminRadioSelect(attrs={"id": "selectielijst-scroll"}),
    )


def get_resultaattype_omschrijving_field(
    db_field: Field, request: HttpRequest, **kwargs
) -> forms.ChoiceField:
    choices = (
        (omschrijving["url"], omschrijving["omschrijving"])
        for omschrijving in get_resultaattype_omschrijvingen()
    )
    return forms.ChoiceField(
        label=db_field.verbose_name.capitalize(),
        choices=choices,
        required=not db_field.blank,
        help_text=db_field.help_text,
    )


def get_processtype_readonly_field(url: str) -> str:
    procestype = retrieve_procestype(url)
    return f"{procestype['nummer']} - {procestype['naam']}"


def get_resultaat_readonly_field(url: str) -> str:
    try:
        resultaat = retrieve_resultaat(url)
        return f"{resultaat['volledigNummer']} - {resultaat['naam']} - {resultaat['waardering']}"
    except InvalidURLError:
        return _(
            "De selectielijstklasse is niet afkomstig uit de Selectielijst API-service"
        )


def get_resultaattype_omschrijving_readonly_field(url: str) -> str:
    try:
        omschrijving = retrieve_resultaattype_omschrijvingen(url)
        return omschrijving["omschrijving"]
    except InvalidURLError:
        return _(
            "De resultaattypeomschrijving is niet afkomstig uit de Selectielijst API-service"
        )
