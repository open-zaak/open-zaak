# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from dataclasses import dataclass
from typing import Union

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, _lazy_re_compile
from django.db import models
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class KardinaliteitValidator:
    """
    Kardinaliteit: gehele getallen groter dan 0, 'N' voor ongelimiteerd
    (Max length of 3 is handled in the CharField)
    """

    def __call__(self, value):
        if value != "N":
            try:
                error = int(value) <= 0
            except Exception:
                error = True
            if error:
                raise ValidationError(
                    _("Gebruik gehele getallen groter dan 0 of 'N' voor ongelimiteerd")
                )


validate_kardinaliteit = KardinaliteitValidator()


uppercase_validator = RegexValidator(
    _lazy_re_compile("^[A-Z]*$"),
    message=_("Voer alleen hoofdletters in."),
    code="invalid",
)


def validate_uppercase(value):
    return uppercase_validator(value)


letters_numbers_underscores_validator = RegexValidator(
    _lazy_re_compile("^[A-Za-z0-9_]*$"),
    message=_("Voer alleen letters, cijfers en/of liggende streepjes in."),
    code="invalid",
)


def validate_letters_numbers_underscores(value):
    """
    Validate a value to only contain letters, numbers and/or underscores.
    """
    return letters_numbers_underscores_validator(value)


letters_numbers_underscores_spaces_validator = RegexValidator(
    _lazy_re_compile("^[A-Za-z0-9 _]*$"),
    message=_("Voer alleen letters, cijfers, liggende streepjes en/of spaties in."),
    code="invalid",
)


def validate_letters_numbers_underscores_spaces(value):
    return letters_numbers_underscores_spaces_validator(value)


@dataclass
class ConceptStatusValidator:
    app_name: str
    model_name: str
    field_name: str

    def __call__(self, instance_or_pk: Union[models.Model, int]):
        obj = instance_or_pk
        if not isinstance(obj, models.Model):
            model = apps.get_model(self.app_name, self.model_name)
            obj = model.objects.get(pk=instance_or_pk)

        if not obj.concept:
            raise ValidationError(
                {
                    self.field_name: _(
                        "Creating a relation to non-concept {resource_name} is forbidden"
                    ).format(resource_name=obj._meta.model_name)
                }
            )


validate_zaaktype_concept = ConceptStatusValidator("catalogi", "ZaakType", "zaaktype")
