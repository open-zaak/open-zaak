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


REFERENTIECODE_IN_USE_MESSAGE = _(
    "Deze referentiecode is al in gebruik door een ander object."
)


def is_referentiecode_in_use(
    model, *, zaaktype, referentiecode, identity_field, identity_value, pk=None
) -> bool:
    """
    Check if ``referentiecode`` is used by a different object of ``model``.

    The code must be globally unique, except for the copies of the same object in
    other versions of the same zaaktype. Those share the zaaktype family
    (catalogus + zaaktype identificatie) and the object identity (``identity_field``,
    e.g. the statustypevolgnummer).
    """
    if not referentiecode or zaaktype is None or identity_value is None:
        return False

    same_object_in_family = models.Q(
        zaaktype__catalogus=zaaktype.catalogus_id,
        zaaktype__identificatie=zaaktype.identificatie,
        **{identity_field: identity_value},
    )
    queryset = model.objects.filter(referentiecode=referentiecode).exclude(
        same_object_in_family
    )
    if pk:
        queryset = queryset.exclude(pk=pk)
    return queryset.exists()
