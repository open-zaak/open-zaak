# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from typing import Optional, Union

from django import forms
from django.contrib.gis.admin.widgets import OpenLayersWidget
from django.contrib.gis.gdal import AxisOrder, OGRGeometry, SpatialReference
from django.contrib.gis.geos import GEOSGeometry
from django.utils.translation import gettext_lazy as _

from dateutil.relativedelta import relativedelta
from relativedeltafield.utils import format_relativedelta, parse_relativedelta


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
        # In case the value was directly injected into the form data, e.g. if validation
        # happens on the backend, simply take that value
        if name in data and isinstance(data[name], relativedelta):
            duration = data[name]
        else:
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
            name=f"{name}_{attribute}",
            value=value,
            attrs=attrs,
        )
        return widget_context["widget"]


class AuthoritySpatialReference(SpatialReference):
    def __init__(self, srs_input="", srs_type="user"):
        super().__init__(srs_input, srs_type, axis_order=AxisOrder.AUTHORITY)


class AuthorityAxisOrderOLWidget(OpenLayersWidget):
    """
    Here is a long and painful explanation why we need it. Buckle up.

    First, `Zaak.zaakgeometry` field is geometric field, not geographic. If it's a point, it has x and y coordinates.
    But how do we map them to lat and lon? What is the order - lat/lon or lon/lat?
    Well, there is no consensus what should be the order.

    OpenZaak supports only "ESPG:4326" coordinate system. According to "ESPG:4326" it should be lat/lon order.
    GDAL<3.0 expects lon/lat order and treat all points like lon/lat.
    Good news, that GDAL>=3.0 can use the order defined in CRS. And in Open Zaak we support GDAL >= 3.0

    BUT django.contrib.gis.gdal uses traditional axis order (lon/lat) as a default one and user can set up only
    SRID without axis order when initializing geometry objects.

    OpenStreetMap supports "ESPG:3587" coordinate system. So in the parent class "ESPG:4326" coordinates are
    transformed to "ESPG:3587" using GDAL api with traditional axis order, where 'x' is treated as 'lon'
    and 'y' is treated as 'lat'

    In this class we transform coordinates with "Authority" order, for "ESPG:4326" it's lat/lon.

    If in next django versions "axis_order" is treated with more attention, this workaround should be removed.
    This workaround won't work if os GDAL<3.0. Perhaps, in this case we can use django-leaflet?

    GDAL related doc - https://gdal.org/tutorials/osr_api_tut.html#crs-and-axis-order
    """

    data_srid = 4326

    def get_context(self, name, value, attrs):
        if value:
            ogr = OGRGeometry(value.wkt, AuthoritySpatialReference(value.srid))
            # ogr = value.ogr
            ogr.transform(self.params["srid"])
            value = GEOSGeometry(ogr._geos_ptr(), srid=ogr.srid)

        return super().get_context(name, value, attrs)

    def deserialize(self, value):
        value = GEOSGeometry(value)

        if value.srid and value.srid != self.data_srid:
            value.transform(AuthoritySpatialReference(self.data_srid))
        return value
