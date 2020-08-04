# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django import forms
from django.contrib import admin

from openzaak.utils.admin import (
    AuditTrailAdminMixin,
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    link_to_related_objects,
)

from .models import Besluit, BesluitInformatieObject


class BesluitInformatieObjectForm(forms.ModelForm):
    class Meta:
        model = BesluitInformatieObject
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("_informatieobject") and not cleaned_data.get(
            "_informatieobject_url"
        ):
            raise forms.ValidationError(
                "Je moet een informatieobject opgeven: "
                "selecteer een informatieobject of vul een externe URL in."
            )

        return cleaned_data


@admin.register(BesluitInformatieObject)
class BesluitInformatieObjectAdmin(
    AuditTrailAdminMixin, UUIDAdminMixin, admin.ModelAdmin
):
    form = BesluitInformatieObjectForm
    list_display = ("besluit", "_informatieobject", "_informatieobject_url")
    list_filter = ("besluit",)
    search_fields = (
        "besluit__uuid",
        "_informatieobject__enkelvoudiginformatieobject__uuid",
        "_informatieobject_url",
    )
    ordering = ("besluit", "_informatieobject", "_informatieobject_url")
    raw_id_fields = ("besluit", "_informatieobject")
    viewset = (
        "openzaak.components.besluiten.api.viewsets.BesluitInformatieObjectViewSet"
    )


class BesluitInformatieObjectInline(EditInlineAdminMixin, admin.TabularInline):
    model = BesluitInformatieObject
    fields = BesluitInformatieObjectAdmin.list_display
    fk_name = "besluit"


class BesluitForm(forms.ModelForm):
    class Meta:
        model = Besluit
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("_besluittype_url") and not cleaned_data.get(
            "_besluittype"
        ):
            raise forms.ValidationError(
                "Je moet een besluittype opgeven: "
                "selecteer een besluittype uit de catalogus of vul een externe URL in."
            )

        return cleaned_data


@admin.register(Besluit)
class BesluitAdmin(
    AuditTrailAdminMixin, ListObjectActionsAdminMixin, UUIDAdminMixin, admin.ModelAdmin
):
    form = BesluitForm
    list_display = ("verantwoordelijke_organisatie", "identificatie", "datum")
    list_filter = ("datum", "ingangsdatum")
    date_hierarchy = "datum"
    search_fields = (
        "verantwoordelijke_organisatie",
        "identificatie",
        "uuid",
    )
    ordering = ("datum", "identificatie")
    raw_id_fields = ("_besluittype", "_zaak")
    inlines = (BesluitInformatieObjectInline,)
    viewset = "openzaak.components.besluiten.api.viewsets.BesluitViewSet"

    def get_object_actions(self, obj):
        return (link_to_related_objects(BesluitInformatieObject, obj),)
