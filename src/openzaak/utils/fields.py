# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Callable

from django.contrib.admin.options import FORMFIELD_FOR_DBFIELD_DEFAULTS
from django.db import models

from relativedeltafield import RelativeDeltaField

from openzaak.forms.fields import RelativeDeltaField as RelativeDeltaFormField


class DurationField(RelativeDeltaField):
    def formfield(self, form_class=None, **kwargs):
        if form_class is None:
            form_class = RelativeDeltaFormField
        return super().formfield(form_class=form_class, **kwargs)


class AliasField(models.Field):
    def __init__(
        self,
        source_field: models.Field,
        allow_write_when: Callable = lambda i: True,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.source_field = source_field
        self.allow_write_when = allow_write_when

    def set_attributes_from_name(self, name):
        super().set_attributes_from_name(name)
        self.column = self.source_field.column

    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only=True)
        setattr(cls, name, self)

    def __get__(self, instance, instance_type=None):
        return getattr(instance, self.source_field.name)

    def __set__(self, instance, value):
        if not self.allow_write_when(instance):
            return
        setattr(instance, self.source_field.name, value)


# register the override, as the upstream RelativeDeltaField registers its own admin
# form field override as well.
FORMFIELD_FOR_DBFIELD_DEFAULTS[DurationField] = {"form_class": RelativeDeltaFormField}
