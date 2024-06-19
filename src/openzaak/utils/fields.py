# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from pathlib import Path
from typing import Callable, List

from django.contrib.admin.options import FORMFIELD_FOR_DBFIELD_DEFAULTS
from django.core import checks, exceptions, validators
from django.db import models
from django.db.models.base import Options
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_loose_fk.fields import FkOrURLField
from relativedeltafield import RelativeDeltaField
from zgw_consumers.models import ServiceUrlField

from openzaak.forms.fields import RelativeDeltaField as RelativeDeltaFormField


class DurationField(RelativeDeltaField):
    def formfield(self, form_class=None, **kwargs):
        if form_class is None:
            form_class = RelativeDeltaFormField
        return super().formfield(form_class=form_class, **kwargs)


class AliasMixin:
    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only=True)
        setattr(cls, name, self)

    def __get__(self, instance, instance_type=None):
        return getattr(instance, self.source_field.name)

    def __set__(self, instance, value):
        if not self.allow_write_when(instance):
            return
        setattr(instance, self.source_field.name, value)


class AliasField(AliasMixin, models.Field):
    def __init__(
        self,
        source_field: models.Field,
        allow_write_when: Callable = lambda i: True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.source_field = source_field
        self.allow_write_when = allow_write_when

    def set_attributes_from_name(self, name):
        super().set_attributes_from_name(name)
        self.column = self.source_field.column


class AliasServiceUrlField(AliasMixin, ServiceUrlField):
    def __init__(
        self,
        source_field: ServiceUrlField,
        allow_write_when: Callable = lambda i: True,
        **kwargs,
    ):
        self.source_field = source_field
        self.allow_write_when = allow_write_when

        super().__init__(
            base_field=source_field.base_field,
            relative_field=source_field.relative_field,
            **kwargs,
        )

    def _add_check_constraint(
        self,
        options: Options,
        name: str = "{prefix}{base_field}_and_{relative_field}_filled",
    ) -> None:
        """
        No constraint for Alias fields
        """
        return


# register the override, as the upstream RelativeDeltaField registers its own admin
# form field override as well.
FORMFIELD_FOR_DBFIELD_DEFAULTS[DurationField] = {"form_class": RelativeDeltaFormField}


class FkOrServiceUrlField(FkOrURLField):
    """
    Support :class:`zgw_consumers.ServiceUrlField` as 'url_field'
    """

    def _add_check_constraint(
        self, options, name="{prefix}{fk_field}_or_{url_base_field}_filled"
    ) -> None:
        """
        Create the DB constraints and add them if they're not present yet.
        """
        if self.null:
            return

        # during migrations, the FK fields are added later, causing the constraint SQL
        # building to blow up. We can ignore this at that time.
        if self.model.__module__ == "__fake__":
            return

        url_base_field = self._url_field.base_field
        # one of both MUST be filled and they cannot be filled both at the
        # same time
        empty_url_base_field = models.Q(**{f"{url_base_field}__isnull": True})
        empty_fk_field = models.Q(**{f"{self.fk_field}__isnull": True})
        fk_filled = ~empty_fk_field & empty_url_base_field
        url_filled = empty_fk_field & ~empty_url_base_field

        constraint = models.CheckConstraint(
            name=name.format(
                prefix=f"{options.app_label}_{options.model_name}_",
                fk_field=self.fk_field,
                url_base_field=url_base_field,
            ),
            check=fk_filled | url_filled,
        )
        options.constraints.append(constraint)
        # ensure this can be picked up by migrations by making it "explicitly defined"
        if "constraints" not in options.original_attrs:
            options.original_attrs["constraints"] = options.constraints
        return

    def check(self, **kwargs) -> List[checks.Error]:
        errors = []
        if not isinstance(self._fk_field, models.ForeignKey):
            errors.append(
                checks.Error(
                    "The field passed to 'fk_field' should be a ForeignKey",
                    obj=self,
                    id="fk_or_url_field.E001",
                )
            )

        if not isinstance(self._url_field, ServiceUrlField):
            errors.append(
                checks.Error(
                    "The field passed to 'url_field' should be a ServiceUrlField",
                    obj=self,
                    id="open_zaak.E001",
                )
            )

        return errors


def validate_relative_url(value):
    message = _("Enter a valid relative URL.")

    if value.startswith(("https://", "http://", "fps://", "ftps://", "/")):
        raise exceptions.ValidationError(
            message, code="invalid", params={"value": value}
        )


class RelativeURLField(models.CharField):
    """
    Model field for relative urls with build-in regex validator
    """

    default_validators = [validate_relative_url]

    def __init__(self, verbose_name=None, name=None, **kwargs):
        kwargs.setdefault("max_length", 1000)
        super().__init__(verbose_name, name, **kwargs)


class ServiceFkField(models.ForeignKey):
    """
    FK to Service model field
    """

    def __init__(self, **kwargs):
        kwargs["to"] = "zgw_consumers.Service"
        kwargs.setdefault("on_delete", models.PROTECT)
        kwargs.setdefault("related_name", "+")  # no reverse relations by default
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)

        super().__init__(**kwargs)


class NLPostcodeValidator(validators.RegexValidator):
    """
    Validation for Dutch postcodes.
    """

    error_message = _("Enter a valid postcode.")
    regex = r"^[1-9][0-9]{3} ?[A-Z]{2}$"


class NLPostcodeField(models.CharField):
    """
    Model field for NL postcodes with build-in regex validator
    """

    default_validators = [NLPostcodeValidator()]

    def __init__(self, verbose_name=None, name=None, **kwargs):
        kwargs.setdefault("max_length", 6)
        super().__init__(verbose_name, name, **kwargs)


def get_default_path(field: models.FileField) -> Path:
    storage_location = Path(field.storage.base_location)
    path = Path(storage_location / field.upload_to)

    now = timezone.now()
    return Path(now.strftime(str(path)))
