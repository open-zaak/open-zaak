# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2020 Dimpact
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.template import Library

from zgw_consumers.constants import APITypes

register = Library()


@register.filter
def boolean_icon(field_val):
    return _boolean_icon(field_val)


@register.filter
def show_api_type(api_type_value):
    # for consistency with external service form
    component_choices = {
        APITypes.ac: "Autorisaties API",
        APITypes.nrc: "Notificaties API",
        APITypes.zrc: "Zaken API",
        APITypes.ztc: "Catalogi API",
        APITypes.drc: "Documenten API",
        APITypes.brc: "Besluiten API",
        APITypes.kic: "Klantinteracties API",
        APITypes.orc: "Overige",
    }
    return component_choices.get(api_type_value, "Overige")
