from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from import_export import resources
from import_export.admin import ImportExportModelAdmin

from openzaak.utils.admin import EditInlineAdminMixin, ListObjectActionsAdminMixin

from ..models import BesluitType, Catalogus, InformatieObjectType, ZaakType
from .besluittype import BesluitTypeAdmin
from .forms import ImportForm
from .informatieobjecttype import InformatieObjectTypeAdmin
from .zaaktypen import ZaakTypeAdmin


class ZaakTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = ZaakType
    fields = ZaakTypeAdmin.list_display
    fk_name = "catalogus"


class BesluitTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = BesluitType
    fields = BesluitTypeAdmin.list_display


class InformatieObjectTypeInline(EditInlineAdminMixin, admin.TabularInline):
    model = InformatieObjectType
    fields = InformatieObjectTypeAdmin.list_display
    fk_name = "catalogus"


class CatalogusResource(resources.ModelResource):
    class Meta:
        model = Catalogus
        exclude = ("id",)
        import_id_fields = ("uuid",)

    def __init__(self, *args, **kwargs):
        import_without_uuids = kwargs.pop("import_without_uuids", False)
        super().__init__(*args, **kwargs)

        # To ensure that new UUIDs are generated if this is desired
        if import_without_uuids:
            self.fields.pop("uuid")
            self._meta.import_id_fields = ("domein",)


@admin.register(Catalogus)
class CatalogusAdmin(ListObjectActionsAdminMixin, ImportExportModelAdmin):
    resource_class = CatalogusResource
    model = Catalogus

    # List
    list_display = ("domein", "rsin", "uuid")
    list_filter = ("domein", "rsin")
    ordering = ("domein", "rsin")
    search_fields = ("domein", "rsin", "contactpersoon_beheer_naam")

    # Details
    fieldsets = (
        (_("Algemeen"), {"fields": ("domein", "rsin")}),
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

    def get_object_actions(self, obj):
        return (
            (
                _("Toon {}").format(ZaakType._meta.verbose_name_plural),
                self._build_changelist_url(ZaakType, query={"catalogus": obj.pk}),
            ),
            (
                _("Toon {}").format(BesluitType._meta.verbose_name_plural),
                self._build_changelist_url(BesluitType, query={"catalogus": obj.pk}),
            ),
            (
                _("Toon {}").format(InformatieObjectType._meta.verbose_name_plural),
                self._build_changelist_url(
                    InformatieObjectType, query={"catalogus": obj.pk}
                ),
            ),
        )

    def get_import_form(self):
        # Use the custom import form which allows importing with or without
        # UUIDs
        return ImportForm

    def get_import_resource_kwargs(self, request, *args, **kwargs):
        data = super().get_import_resource_kwargs(request, *args, **kwargs)

        if request.POST.get("generate_new_uuids", None) == "on":
            self.import_without_uuids = True

        if getattr(self, "import_without_uuids", False):
            data["import_without_uuids"] = True
        return data
