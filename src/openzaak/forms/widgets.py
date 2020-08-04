# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Optional, Union

from django import forms
from django.utils.translation import ugettext_lazy as _

from dateutil.relativedelta import relativedelta
from relativedeltafield import format_relativedelta, parse_relativedelta


class BooleanRadio(forms.RadioSelect):
    def __init__(self, attrs=None):
        choices = ((True, _("Yes")), (False, _("No")))
        super().__init__(attrs, choices)

    def value_from_datadict(self, data, files, name):
        value = data.get(name, False)
        return {True: True, "True": True, "False": False, False: False}[value]


class SplitRelativeDeltaWidget(forms.Widget):
    """
    Present durations as a split widget.

    Given a duration and the ISO8601 duration format, provide an input for
    every component of the duration. Year, months and days are always
    presented, the remaining components only if they have a value set.

    .. note:: fractional durations are currently not support, such as P0.5Y
    """

    template_name = "admin/widgets/split_relative_delta.html"

    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += "_0"
        return id_

    def value_from_datadict(self, data, files, name) -> str:
        value_from_datadict = forms.NumberInput().value_from_datadict

        years = value_from_datadict(data, files, f"{name}_years")
        months = value_from_datadict(data, files, f"{name}_months")
        days = value_from_datadict(data, files, f"{name}_days")
        hours = value_from_datadict(data, files, f"{name}_hours")
        minutes = value_from_datadict(data, files, f"{name}_minutes")
        seconds = value_from_datadict(data, files, f"{name}_seconds")
        microseconds = value_from_datadict(data, files, f"{name}_microseconds")
        duration = relativedelta(
            years=int(years or 0),
            months=int(months or 0),
            days=int(days or 0),
            hours=int(hours or 0),
            minutes=int(minutes or 0),
            seconds=int(seconds or 0),
            microseconds=int(microseconds or 0),
        )
        return format_relativedelta(duration)

    def get_context(self, name, value: Union[relativedelta, str], attrs=None):
        attrs = {} if attrs is None else attrs
        context = super().get_context(name, value, attrs)

        value = value or relativedelta()
        final_attrs = self.build_attrs(attrs)
        final_attrs.update({"min": 0})

        if isinstance(value, str):
            value = parse_relativedelta(value)

        years_widget = self._build_subwidget_context(
            name, value, final_attrs, "years", _("# jaren"), required=True
        )
        months_widget = self._build_subwidget_context(
            name, value, final_attrs, "months", _("# maanden"), required=True
        )
        days_widget = self._build_subwidget_context(
            name, value, final_attrs, "days", _("# dagen"), required=True
        )
        hours_widget = self._build_subwidget_context(
            name, value, final_attrs, "hours", _("# uren")
        )
        minutes_widget = self._build_subwidget_context(
            name, value, final_attrs, "minutes", _("# minuten")
        )
        seconds_widget = self._build_subwidget_context(
            name, value, final_attrs, "seconds", _("# seconden")
        )
        microseconds_widget = self._build_subwidget_context(
            name, value, final_attrs, "microseconds", _("# microseconden")
        )
        subwidgets = [
            years_widget,
            months_widget,
            # weeks is skipped, because internally it's converted to days
            days_widget,
            hours_widget,
            minutes_widget,
            seconds_widget,
            microseconds_widget,
        ]
        context["widget"]["subwidgets"] = [
            widget for widget in subwidgets if widget is not None
        ]
        return context

    def _get_subwidget_value(self, value: relativedelta, attr: str) -> Optional[int]:
        if not value:
            return None
        return getattr(value, attr) or None

    def _build_subwidget_context(
        self,
        name: str,
        value: relativedelta,
        final_attrs: dict,
        attribute: str,
        placeholder,
        required: bool = False,
    ) -> Optional[forms.Widget]:
        value = self._get_subwidget_value(value, attribute)
        if value is None and not required:
            return None

        id_ = final_attrs.get("id")
        attrs = {
            **final_attrs,
            "placeholder": placeholder,
            "title": placeholder,
        }
        if id_:
            attrs["id"] = f"{id_}_{attribute}"
        widget_context = forms.NumberInput().get_context(
            name=f"{name}_{attribute}", value=value, attrs=attrs,
        )
        return widget_context["widget"]
