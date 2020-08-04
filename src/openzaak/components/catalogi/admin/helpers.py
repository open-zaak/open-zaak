# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib.admin.helpers import (
    AdminField,
    AdminForm as _AdminForm,
    AdminReadonlyField as _AdminReadonlyField,
    Fieldline as _Fieldline,
    Fieldset as _Fieldset,
)
from django.contrib.admin.utils import (
    display_for_field as _display_for_field,
    lookup_field,
)
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.fields.related import ManyToManyRel
from django.template.defaultfilters import linebreaksbr
from django.utils.html import conditional_escape, mark_safe, urlize

from openzaak.utils.fields import DurationField

from .utils import format_duration

# all helper classes below are used to able to modify read_only field content


class AdminForm(_AdminForm):
    def __init__(
        self, callback_readonly, *args, **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.callback_readonly = callback_readonly

    def __iter__(self):
        for name, options in self.fieldsets:
            yield Fieldset(
                self.callback_readonly,
                self.form,
                name,
                readonly_fields=self.readonly_fields,
                model_admin=self.model_admin,
                **options,
            )


class Fieldset(_Fieldset):
    def __init__(self, callback_readonly, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback_readonly = callback_readonly

    def __iter__(self):
        for field in self.fields:
            yield Fieldline(
                self.callback_readonly,
                self.form,
                field,
                self.readonly_fields,
                model_admin=self.model_admin,
            )


class Fieldline(_Fieldline):
    def __init__(self, callback_readonly, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback_readonly = callback_readonly

    def __iter__(self):
        for i, field in enumerate(self.fields):
            if field in self.readonly_fields:
                yield AdminReadonlyField(
                    self.callback_readonly,
                    self.form,
                    field,
                    is_first=(i == 0),
                    model_admin=self.model_admin,
                )
            else:
                yield AdminField(self.form, field, is_first=(i == 0))


class AdminReadonlyField(_AdminReadonlyField):
    def __init__(self, callback_readonly, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback_readonly = callback_readonly

    def contents(self):
        from django.contrib.admin.templatetags.admin_list import _boolean_icon

        field, obj, model_admin = (
            self.field["field"],
            self.form.instance,
            self.model_admin,
        )
        try:
            f, attr, value = lookup_field(field, obj, model_admin)
        except (AttributeError, ValueError, ObjectDoesNotExist):
            result_repr = self.empty_value_display
        else:
            if field in self.form.fields:
                widget = self.form[field].field.widget
                # This isn't elegant but suffices for contrib.auth's
                # ReadOnlyPasswordHashWidget.
                if getattr(widget, "read_only", False):
                    return widget.render(field, value)
            if f is None:
                if getattr(attr, "boolean", False):
                    result_repr = _boolean_icon(value)
                else:
                    if hasattr(value, "__html__"):
                        result_repr = value
                    else:
                        result_repr = linebreaksbr(value)
            else:
                if isinstance(f.remote_field, ManyToManyRel) and value is not None:
                    result_repr = ", ".join(map(str, value.all()))
                else:
                    result_repr = display_for_field(value, f, self.empty_value_display)

                result_repr = self.callback_readonly(f, result_repr, value)
                result_repr = linebreaksbr(result_repr)

        return conditional_escape(result_repr)


def display_for_field(value, field, empty_value_display):
    if not value:
        return _display_for_field(value, field, empty_value_display)

    if isinstance(field, models.URLField):
        return mark_safe(urlize(value))

    if isinstance(field, DurationField):
        res = format_duration(value)
        return res

    if isinstance(field, ArrayField):
        formatted_parts = []
        for value_part in value:
            formatted_parts.append(
                display_for_field(value_part, field.base_field, empty_value_display)
            )

        formatted = "\n".join(formatted_parts)
        return mark_safe(formatted)

    return _display_for_field(value, field, empty_value_display)
