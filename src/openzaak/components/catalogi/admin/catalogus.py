# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
from django.apps import apps
from django.contrib import admin
from django.urls import path
from django.utils.translation import ugettext_lazy as _

from openzaak.utils.admin import (
    EditInlineAdminMixin,
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    link_to_related_objects,
)

from ..models import (
    BesluitType,
    Catalogus,
    InformatieObjectType,
    ZaakType,
    ZaakTypeInformatieObjectType,
)
from .admin_views import (
    CatalogusZaakTypeImportSelectView,
    CatalogusZaakTypeImportUploadView,
)
from .mixins import ExportMixin, ImportMixin


class ZaakTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakType
    fields = (
        "zaaktype_omschrijving",
        "identificatie",
        "versiedatum",
    )
    fk_name = "catalogus"


class BesluitTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = BesluitType
    fields = (
        "omschrijving",
        "besluitcategorie",
        "catalogus",
    )


class InformatieObjectTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = InformatieObjectType
    fields = (
        "omschrijving",
        "catalogus",
    )
    fk_name = "catalogus"


@admin.register(Catalogus)
class CatalogusAdmin(
    ListObjectActionsAdminMixin,
    UUIDAdminMixin,
    ExportMixin,
    ImportMixin,
    admin.ModelAdmin,
):
    model = Catalogus
    change_list_template = "admin/catalogi/change_list_catalogus.html"
    change_form_template = "admin/catalogi/change_form_catalogus.html"

    # List
    list_display = ("_admin_name", "domein", "rsin")
    list_filter = ("domein", "rsin")
    ordering = ("domein", "rsin")
    search_fields = (
        "uuid",
        "_admin_name",
        "domein",
        "rsin",
        "contactpersoon_beheer_naam",
    )

    # Details
    fieldsets = (
        (_("Algemeen"), {"fields": ("_admin_name", "domein", "rsin", "uuid",)}),
        (
            _("Contactpersoon beheer"),
            {
                "fields": (
                    "contactpersoon_beheer_naam",
                    "contactpersoon_beheer_telefoonnummer",
                    "contactpersoon_beheer_emailadres",
                )
            },
        ),
    )
    inlines = (ZaakTypeInline, BesluitTypeInline, InformatieObjectTypeInline)
    readonly_fields = ("uuid",)

    # For import/export mixins
    resource_name = "catalogus"

    def get_related_objects(self, obj):
        resources = {}

        resources["Catalogus"] = [obj.pk]

        # Resources with foreign keys to catalogus
        fields = ["InformatieObjectType", "BesluitType", "ZaakType"]
        for field in fields:
            resources[field] = list(
                getattr(obj, f"{field.lower()}_set").values_list("pk", flat=True)
            )
        resources["ZaakTypeInformatieObjectType"] = list(
            ZaakTypeInformatieObjectType.objects.filter(
                zaaktype__in=resources["ZaakType"],
                informatieobjecttype__in=resources["InformatieObjectType"],
            ).values_list("pk", flat=True)
        )

        # Resources with foreign keys to  ZaakType
        fields = ["ResultaatType", "RolType", "StatusType", "Eigenschap"]
        for field in fields:
            model = apps.get_model("catalogi", field)
            resources[field] = list(
                model.objects.filter(zaaktype__in=resources["ZaakType"]).values_list(
                    "pk", flat=True
                )
            )

        resource_list = []
        id_list = []
        for resource, ids in resources.items():
            if ids:
                resource_list.append(resource)
                id_list.append(ids)

        return resource_list, id_list

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<path:catalogus_pk>/zaaktype/import/",
                self.admin_site.admin_view(CatalogusZaakTypeImportUploadView.as_view()),
                name="catalogi_catalogus_import_zaaktype",
            ),
            path(
                "<path:catalogus_pk>/zaaktype/import/select",
                self.admin_site.admin_view(CatalogusZaakTypeImportSelectView.as_view()),
                name="catalogi_catalogus_import_zaaktype_select",
            ),
        ]
        return my_urls + urls

    def get_object_actions(self, obj):
        return (
            link_to_related_objects(ZaakType, obj),
            link_to_related_objects(BesluitType, obj),
            link_to_related_objects(InformatieObjectType, obj),
        )
